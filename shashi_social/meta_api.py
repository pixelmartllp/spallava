"""Meta Graph API client for publishing to a Facebook Page and Instagram.

Facebook accepts a direct file upload. Instagram does not - it needs a public
image URL. Rather than depending on a third-party image host, we upload the
photo to the Facebook Page as an *unpublished* photo, take the CDN URL Meta
hands back, and feed that to the Instagram container. Everything stays inside
Meta and no extra account is needed.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from . import brand

CONFIG_FILE = brand.ROOT / "config.json"
DEFAULT_API_VERSION = "v25.0"
GRAPH = "https://graph.facebook.com"

# Instagram rejects containers that never finish processing; cap the wait.
IG_POLL_ATTEMPTS = 30
IG_POLL_SECONDS = 3

REQUIRED_KEYS = ("page_id", "access_token")


class MetaAPIError(RuntimeError):
    """A Graph API call failed. Carries the message Meta actually returned."""

    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}


class ConfigError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

def load_config() -> dict[str, Any]:
    """Read config.json, then fill any gaps from environment variables.

    config.json wins on purpose. The META_* names are generic enough that
    another project on the same machine can set them user-wide, and if the
    environment took priority this pipeline would silently publish against
    somebody else's Page. In the cloud there is no config.json, so the
    workflow's secrets become the only source and everything still works.
    """
    config: dict[str, Any] = {}
    if CONFIG_FILE.is_file():
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"config.json is not valid JSON: {exc}") from exc

    config = {k: v for k, v in config.items()
              if not str(k).startswith("_") and not _is_placeholder(v)}

    env_map = {
        "app_id": "META_APP_ID",
        "app_secret": "META_APP_SECRET",
        "page_id": "META_PAGE_ID",
        "ig_user_id": "META_IG_USER_ID",
        "access_token": "META_ACCESS_TOKEN",
        "api_version": "META_API_VERSION",
    }
    for key, env in env_map.items():
        if config.get(key):
            continue
        value = os.environ.get(env)
        if value and not _is_placeholder(value):
            config[key] = value

    config.setdefault("api_version", DEFAULT_API_VERSION)
    return config


def _is_placeholder(value: Any) -> bool:
    """Treat untouched template values as missing.

    Otherwise copying config.example.json makes the setup look complete and
    the first API call fails with a confusing token error instead of a clear
    "you have not filled this in yet".
    """
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return not stripped or stripped.startswith("YOUR_")


def config_status() -> dict[str, Any]:
    """What is configured - without ever echoing the token back."""
    config = load_config()
    token = str(config.get("access_token") or "")
    return {
        "config_file": str(CONFIG_FILE),
        "config_file_exists": CONFIG_FILE.is_file(),
        "app_id_set": bool(config.get("app_id")),
        "app_secret_set": bool(config.get("app_secret")),
        "page_id": config.get("page_id") or None,
        "ig_user_id": config.get("ig_user_id") or None,
        "access_token_set": bool(token),
        "access_token_preview": (token[:6] + "..." + token[-4:]) if len(token) > 12 else None,
        "api_version": config.get("api_version"),
        "ready_for_facebook": all(config.get(k) for k in REQUIRED_KEYS),
        "ready_for_instagram": all(config.get(k) for k in REQUIRED_KEYS)
                               and bool(config.get("ig_user_id")),
    }


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------

class GraphClient:
    def __init__(self, config: dict[str, Any] | None = None, timeout: int = 120):
        self.config = config or load_config()
        self.timeout = timeout
        missing = [k for k in REQUIRED_KEYS if not self.config.get(k)]
        if missing:
            raise ConfigError(
                f"Missing Meta credentials: {', '.join(missing)}. "
                f"Fill them into {CONFIG_FILE} or set the META_* environment "
                f"variables. See SETUP.md for how to get them."
            )
        self.token = str(self.config["access_token"])
        self.page_id = str(self.config["page_id"])
        self.ig_user_id = str(self.config.get("ig_user_id") or "")
        self.base = f"{GRAPH}/{self.config.get('api_version', DEFAULT_API_VERSION)}"
        self._page_token: str | None = None

    # -- plumbing ---------------------------------------------------------

    @property
    def page_token(self) -> str:
        """The token to publish with - always the Page's own token.

        Content has to be created *as the Page*. A user or system-user token
        fails with a misleading "publish_actions is deprecated" error, so we
        exchange whatever was configured for the Page token once and cache it.
        """
        if self._page_token is None:
            try:
                response = self._request("GET", self.page_id,
                                         params={"fields": "access_token"})
                self._page_token = response.get("access_token") or self.token
            except MetaAPIError:
                # Already a Page token, or the field is not exposed - the
                # configured token is the best we have.
                self._page_token = self.token
        return self._page_token

    def _request(self, method: str, path: str, *, params: dict | None = None,
                 data: dict | None = None, files: dict | None = None,
                 as_page: bool = False) -> dict:
        url = f"{self.base}/{path.lstrip('/')}"
        params = dict(params or {})
        params.setdefault("access_token", self.page_token if as_page else self.token)

        try:
            response = requests.request(method, url, params=params, data=data,
                                        files=files, timeout=self.timeout)
        except requests.RequestException as exc:
            raise MetaAPIError(f"Network error calling {path}: {exc}") from exc

        try:
            payload = response.json()
        except ValueError:
            raise MetaAPIError(
                f"Graph API returned non-JSON (HTTP {response.status_code}) "
                f"for {path}: {response.text[:300]}"
            ) from None

        if isinstance(payload, dict) and "error" in payload:
            err = payload["error"]
            raise MetaAPIError(
                f"{err.get('type', 'GraphError')} "
                f"(code {err.get('code')}): {err.get('message')}",
                payload,
            )
        if not response.ok:
            raise MetaAPIError(f"HTTP {response.status_code} for {path}: {payload}",
                               payload if isinstance(payload, dict) else None)
        return payload

    def get(self, path: str, **params) -> dict:
        return self._request("GET", path, params=params)

    # -- diagnostics ------------------------------------------------------

    def verify(self) -> dict[str, Any]:
        """Check the token, the Page and the linked Instagram account."""
        result: dict[str, Any] = {"ok": True, "checks": {}, "problems": []}

        try:
            page = self.get(self.page_id, fields="id,name,link,fan_count")
            result["checks"]["page"] = page
        except MetaAPIError as exc:
            result["ok"] = False
            result["problems"].append(f"Page check failed: {exc}")

        try:
            token_info = self.get("debug_token", input_token=self.token)
            data = token_info.get("data", {})
            expires = data.get("expires_at")
            result["checks"]["token"] = {
                "type": data.get("type"),
                "app_id": data.get("app_id"),
                "is_valid": data.get("is_valid"),
                "expires_at": expires,
                "never_expires": expires == 0,
                "scopes": data.get("scopes"),
            }
            if not data.get("is_valid"):
                result["ok"] = False
                result["problems"].append("Access token is not valid.")
            for scope in ("pages_manage_posts", "pages_read_engagement"):
                if scope not in (data.get("scopes") or []):
                    result["problems"].append(f"Token is missing scope: {scope}")
        except MetaAPIError as exc:
            result["problems"].append(f"Token introspection failed: {exc}")

        if self.ig_user_id:
            try:
                ig = self.get(self.ig_user_id,
                              fields="id,username,followers_count,media_count")
                result["checks"]["instagram"] = ig
            except MetaAPIError as exc:
                result["ok"] = False
                result["problems"].append(f"Instagram check failed: {exc}")
        else:
            result["problems"].append(
                "No ig_user_id configured - Instagram posting is disabled."
            )

        return result

    def discover(self) -> dict[str, Any]:
        """List the Pages this token can manage and their linked IG accounts.

        Useful for filling in page_id / ig_user_id the first time.
        """
        pages = self.get("me/accounts",
                         fields="id,name,link,instagram_business_account{id,username}")
        found = []
        for page in pages.get("data", []):
            ig = page.get("instagram_business_account") or {}
            found.append({
                "page_id": page.get("id"),
                "page_name": page.get("name"),
                "page_link": page.get("link"),
                "ig_user_id": ig.get("id"),
                "ig_username": ig.get("username"),
            })
        return {"pages": found}

    # -- publishing -------------------------------------------------------

    def post_facebook_photo(self, image_path: Path, caption: str,
                            published: bool = True,
                            temporary: bool = False) -> dict[str, Any]:
        """Upload a photo to the Page. Returns the Graph response."""
        image_path = Path(image_path)
        if not image_path.is_file():
            raise MetaAPIError(f"Image not found: {image_path}")

        data = {
            "caption" if not published else "message": caption,
            "published": "true" if published else "false",
        }
        if temporary:
            data["temporary"] = "true"

        with open(image_path, "rb") as handle:
            files = {"source": (image_path.name, handle, "image/jpeg")}
            return self._request("POST", f"{self.page_id}/photos",
                                 data=data, files=files, as_page=True)

    def get_photo_url(self, photo_id: str) -> str:
        """Largest CDN URL for an already-uploaded photo."""
        info = self._request("GET", photo_id, params={"fields": "images"},
                             as_page=True)
        images = info.get("images") or []
        if not images:
            raise MetaAPIError(f"Photo {photo_id} has no image URLs yet.")
        best = max(images, key=lambda i: i.get("width", 0) * i.get("height", 0))
        url = best.get("source")
        if not url:
            raise MetaAPIError(f"Photo {photo_id} returned no source URL.")
        return url

    def host_image(self, image_path: Path) -> tuple[str, str]:
        """Get a public URL for a local image, via an unpublished Page photo.

        Returns (public_url, photo_id) so the caller can delete it afterwards.
        """
        response = self.post_facebook_photo(image_path, caption="",
                                            published=False, temporary=True)
        photo_id = response.get("id")
        if not photo_id:
            raise MetaAPIError(f"Unpublished upload returned no id: {response}")
        return self.get_photo_url(photo_id), photo_id

    def delete_object(self, object_id: str) -> bool:
        try:
            self._request("DELETE", object_id, as_page=True)
            return True
        except MetaAPIError:
            return False

    def post_instagram_photo(self, caption: str,
                             image_path: Path | None = None,
                             image_url: str | None = None) -> dict[str, Any]:
        """Create an Instagram container and publish it."""
        if not self.ig_user_id:
            raise ConfigError(
                "ig_user_id is not configured - cannot post to Instagram. "
                "Run discover_meta_accounts to find it."
            )

        scratch_photo_id: str | None = None
        if image_url is None:
            if image_path is None:
                raise ValueError("Provide either image_path or image_url.")
            image_url, scratch_photo_id = self.host_image(Path(image_path))

        try:
            container = self._request(
                "POST", f"{self.ig_user_id}/media",
                data={"image_url": image_url, "caption": caption},
                as_page=True,
            )
            creation_id = container.get("id")
            if not creation_id:
                raise MetaAPIError(f"No container id returned: {container}")

            self._await_container(creation_id)

            published = self._request(
                "POST", f"{self.ig_user_id}/media_publish",
                data={"creation_id": creation_id}, as_page=True,
            )
            return {
                "media_id": published.get("id"),
                "creation_id": creation_id,
                "image_url": image_url,
            }
        finally:
            if scratch_photo_id:
                self.delete_object(scratch_photo_id)

    def _await_container(self, creation_id: str) -> None:
        """Block until Instagram finishes processing the container."""
        last = "UNKNOWN"
        for _ in range(IG_POLL_ATTEMPTS):
            status = self._request("GET", creation_id,
                                   params={"fields": "status_code,status"},
                                   as_page=True)
            last = status.get("status_code", "UNKNOWN")
            if last == "FINISHED":
                return
            if last in ("ERROR", "EXPIRED"):
                raise MetaAPIError(
                    f"Instagram container {creation_id} failed with "
                    f"{last}: {status.get('status')}"
                )
            time.sleep(IG_POLL_SECONDS)
        raise MetaAPIError(
            f"Instagram container {creation_id} still {last} after "
            f"{IG_POLL_ATTEMPTS * IG_POLL_SECONDS}s."
        )

    # -- insights ---------------------------------------------------------

    def recent_posts(self, limit: int = 10) -> dict[str, Any]:
        return self._request(
            "GET", f"{self.page_id}/posts",
            params={"fields": "id,message,created_time,permalink_url",
                    "limit": limit},
            as_page=True)


# --------------------------------------------------------------------------
# Token helpers
# --------------------------------------------------------------------------

def exchange_for_long_lived(app_id: str, app_secret: str,
                            short_lived_token: str,
                            api_version: str = DEFAULT_API_VERSION) -> dict[str, Any]:
    """Turn a ~1 hour user token into a ~60 day one."""
    url = f"{GRAPH}/{api_version}/oauth/access_token"
    response = requests.get(url, timeout=60, params={
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token,
    })
    payload = response.json()
    if "error" in payload:
        raise MetaAPIError(payload["error"].get("message", str(payload)), payload)
    return payload


def page_token_from_user_token(user_token: str, page_id: str,
                               api_version: str = DEFAULT_API_VERSION) -> str:
    """Fetch the Page access token. Derived from a long-lived user token it
    does not expire, which is what makes unattended daily posting possible."""
    url = f"{GRAPH}/{api_version}/me/accounts"
    response = requests.get(url, timeout=60,
                            params={"access_token": user_token, "limit": 100})
    payload = response.json()
    if "error" in payload:
        raise MetaAPIError(payload["error"].get("message", str(payload)), payload)
    for page in payload.get("data", []):
        if str(page.get("id")) == str(page_id):
            return page["access_token"]
    names = [f"{p.get('name')} ({p.get('id')})" for p in payload.get("data", [])]
    raise MetaAPIError(
        f"Page {page_id} not found in this user's Pages. Available: {names or 'none'}"
    )
