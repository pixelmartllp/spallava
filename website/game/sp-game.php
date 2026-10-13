<?php
/**
 * SP Game - Brain Game, Missions and Wallet for shashipallava.com.
 *
 * Runs as a Code Snippets snippet (scope: global). Published by
 * website/tools/push_game.py, which strips the opening tag. Everything that
 * decides points lives here, on the server: the browser only ever sees
 * questions without answers, and every award is checked against the bank,
 * the player's history and a daily cap. 1 point = Rs 1, so treat every
 * number below as money.
 *
 * Storage
 *   options    sp_g_bank (questions with answers), sp_g_js, sp_g_css,
 *              sp_g_requests (redeem requests), sp_g_reflections
 *   user meta  sp_points, sp_ledger, sp_phone, sp_tried, sp_correct,
 *              sp_day, sp_day_pts, sp_missions
 */

if ( ! defined( 'ABSPATH' ) ) {
	return;
}

/* ---------------------------------------------------------------- settings */

function sp_g_conf() {
	return array(
		'per_level'    => array( 1 => 1, 2 => 1, 3 => 1, 4 => 2, 5 => 2, 6 => 2, 7 => 3, 8 => 3, 9 => 4, 10 => 4 ),
		'daily_cap'    => 30,   // most points the Brain Game can award in one day
		'unlock'       => 15,   // distinct correct answers in a level to open the next
		'guest_levels' => 2,    // levels a visitor can play without an account
		'round'        => 10,
		'signup_bonus' => 10,
		'mission_max'  => 100,  // cap on any single mission's points, whatever the page says
		'min_redeem'   => 100,
		'mind_points'  => 2,    // every first right answer in the Mindset Challenge
		'mind_unlock'  => 8,    // of 12 per Mindset level
		'mind_levels'  => 5,
		'mind_guest'   => 1,
		'items'        => array( '1:1 session', 'Silver membership', 'Gold membership', 'Platinum membership' ),
	);
}

/* ---------------------------------------------------------------- helpers */

function sp_g_bank() {
	static $bank = null;
	if ( null === $bank ) {
		$bank = get_option( 'sp_g_bank', array() );
		if ( ! is_array( $bank ) ) {
			$bank = array();
		}
	}
	return $bank;
}

function sp_g_meta( $uid, $key, $default ) {
	$v = get_user_meta( $uid, $key, true );
	return ( '' === $v || null === $v ) ? $default : $v;
}

function sp_g_today() {
	return wp_date( 'Y-m-d' );
}

/** add (or, negative, take) points and write the ledger line */
function sp_g_award( $uid, $delta, $note ) {
	$points = (int) sp_g_meta( $uid, 'sp_points', 0 ) + (int) $delta;
	update_user_meta( $uid, 'sp_points', $points );
	$ledger = sp_g_meta( $uid, 'sp_ledger', array() );
	array_unshift( $ledger, array( 't' => time(), 'd' => (int) $delta, 'n' => $note ) );
	update_user_meta( $uid, 'sp_ledger', array_slice( $ledger, 0, 150 ) );
	return $points;
}

/** the track a question belongs to: "iq" (Brain Game) or "mind" (Mindset Challenge) */
function sp_g_track( $q ) {
	return ( isset( $q['tr'] ) && 'mind' === $q['tr'] ) ? 'mind' : 'iq';
}

/** distinct correct answers per level of one track, and the highest level open */
function sp_g_progress( $uid, $track = 'iq' ) {
	$conf    = sp_g_conf();
	$mind    = ( 'mind' === $track );
	$levels  = $mind ? $conf['mind_levels'] : 10;
	$unlock  = $mind ? $conf['mind_unlock'] : $conf['unlock'];
	$bank    = sp_g_bank();
	$correct = $uid ? sp_g_meta( $uid, 'sp_correct', array() ) : array();
	$per     = array_fill( 1, $levels, 0 );
	$size    = array_fill( 1, $levels, 0 );
	foreach ( $bank as $qid => $q ) {
		if ( sp_g_track( $q ) !== $track ) {
			continue;
		}
		$lvl = (int) $q['l'];
		if ( $lvl < 1 || $lvl > $levels ) {
			continue;
		}
		$size[ $lvl ]++;
		if ( isset( $correct[ $qid ] ) ) {
			$per[ $lvl ]++;
		}
	}
	$open = $uid ? 1 : ( $mind ? $conf['mind_guest'] : $conf['guest_levels'] );
	if ( $uid ) {
		for ( $l = 1; $l < $levels; $l++ ) {
			if ( $per[ $l ] >= $unlock ) {
				$open = $l + 1;
			} else {
				break;
			}
		}
	}
	return array( 'correct' => $per, 'size' => $size, 'open' => $open, 'levels' => $levels, 'unlock' => $unlock );
}

function sp_g_day_left( $uid ) {
	$conf = sp_g_conf();
	if ( sp_g_meta( $uid, 'sp_day', '' ) !== sp_g_today() ) {
		return $conf['daily_cap'];
	}
	return max( 0, $conf['daily_cap'] - (int) sp_g_meta( $uid, 'sp_day_pts', 0 ) );
}

function sp_g_is_admin() {
	return current_user_can( 'manage_options' );
}

function sp_g_me() {
	$uid = get_current_user_id();
	$out = array(
		'logged_in' => (bool) $uid,
		'is_admin'  => sp_g_is_admin(),
		'conf'      => array_intersect_key( sp_g_conf(), array_flip( array( 'per_level', 'daily_cap', 'unlock', 'guest_levels', 'min_redeem', 'items', 'signup_bonus', 'mind_points', 'mind_unlock', 'mind_levels' ) ) ),
		'progress'  => sp_g_progress( $uid ),
		'progress_mind' => sp_g_progress( $uid, 'mind' ),
	);
	if ( $uid ) {
		$u                = wp_get_current_user();
		$out['name']      = $u->display_name;
		$out['email']     = $u->user_email;
		$out['joined']    = strtotime( $u->user_registered );
		$out['phone']     = sp_g_meta( $uid, 'sp_phone', '' );
		$out['missions_done'] = count( sp_g_meta( $uid, 'sp_missions', array() ) );
		$out['points']    = (int) sp_g_meta( $uid, 'sp_points', 0 );
		$out['day_left']  = sp_g_day_left( $uid );
		$out['ledger']    = array_slice( sp_g_meta( $uid, 'sp_ledger', array() ), 0, 40 );
		$mine             = array();
		foreach ( get_option( 'sp_g_requests', array() ) as $r ) {
			if ( (int) $r['uid'] === $uid ) {
				$mine[] = array_intersect_key( $r, array_flip( array( 'id', 'item', 'points', 'status', 'at' ) ) );
			}
		}
		$out['requests'] = array_slice( $mine, 0, 20 );
	}
	return $out;
}

/** small per-IP throttle for the open endpoints */
function sp_g_throttle( $what, $limit, $seconds ) {
	$ip  = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : 'x';
	$key = 'sp_g_' . $what . '_' . md5( $ip );
	$n   = (int) get_transient( $key );
	if ( $n >= $limit ) {
		return false;
	}
	set_transient( $key, $n + 1, $seconds );
	return true;
}

function sp_g_err( $code, $msg, $status = 400 ) {
	return new WP_Error( $code, $msg, array( 'status' => $status ) );
}

/* ---------------------------------------------------------------- missions page */

/**
 * The page with slug "missions" holds the month, written by hand:
 *   Month: October 2026
 *   Theme: ...
 *   Week 1 | 20 | Title | What to do
 * Points come from the page but are capped by mission_max.
 */
function sp_g_missions() {
	$page = get_page_by_path( 'missions' );
	if ( ! $page || 'publish' !== $page->post_status ) {
		return array( 'month' => '', 'theme' => '', 'weeks' => array() );
	}
	$text  = wp_strip_all_tags( str_replace( array( '</p>', '<br>', '<br />', '<br/>' ), "\n", $page->post_content ) );
	$month = '';
	$theme = '';
	$weeks = array();
	foreach ( preg_split( '/\r?\n/', html_entity_decode( $text, ENT_QUOTES, 'UTF-8' ) ) as $line ) {
		$line = trim( $line );
		if ( 0 === stripos( $line, 'month:' ) ) {
			$month = trim( substr( $line, 6 ) );
		} elseif ( 0 === stripos( $line, 'theme:' ) ) {
			$theme = trim( substr( $line, 6 ) );
		} elseif ( preg_match( '/^week\s*(\d)\s*\|\s*(\d+)\s*\|\s*([^|]+)\|\s*(.+)$/i', $line, $m ) ) {
			$n       = (int) $m[1];
			$weeks[] = array(
				'week'   => $n,
				'id'     => sanitize_title( $month ) . '-w' . $n,
				'points' => min( (int) $m[2], sp_g_conf()['mission_max'] ),
				'title'  => trim( $m[3] ),
				'desc'   => trim( $m[4] ),
				'opens'  => 1 + 7 * ( $n - 1 ),
			);
		}
	}
	$day   = (int) wp_date( 'j' );
	$uid   = get_current_user_id();
	$done  = $uid ? sp_g_meta( $uid, 'sp_missions', array() ) : array();
	foreach ( $weeks as &$w ) {
		$w['open'] = $day >= $w['opens'];
		$w['done'] = isset( $done[ $w['id'] ] );
	}
	unset( $w );
	return array( 'month' => $month, 'theme' => $theme, 'weeks' => $weeks );
}

/* ---------------------------------------------------------------- REST */

add_action( 'rest_api_init', function () {
	$ns     = 'sp/v1';
	$open   = '__return_true';
	$member = function () {
		return is_user_logged_in();
	};
	$admin  = function () {
		return sp_g_is_admin();
	};

	register_rest_route( $ns, '/me', array( 'methods' => 'GET', 'permission_callback' => $open, 'callback' => function () {
		return sp_g_me();
	} ) );

	register_rest_route( $ns, '/register', array( 'methods' => 'POST', 'permission_callback' => $open, 'callback' => function ( $req ) {
		if ( '' !== (string) $req->get_param( 'website' ) ) {
			return sp_g_err( 'sp_spam', 'Please try again.' );
		}
		if ( ! sp_g_throttle( 'reg', 5, HOUR_IN_SECONDS ) ) {
			return sp_g_err( 'sp_slow', 'Too many sign-ups from here. Please try later.', 429 );
		}
		$name  = sanitize_text_field( (string) $req->get_param( 'name' ) );
		$email = sanitize_email( (string) $req->get_param( 'email' ) );
		$phone = preg_replace( '/\D/', '', (string) $req->get_param( 'phone' ) );
		$pass  = (string) $req->get_param( 'password' );
		if ( 12 === strlen( $phone ) && 0 === strpos( $phone, '91' ) ) {
			$phone = substr( $phone, 2 );
		}
		if ( strlen( $name ) < 2 ) {
			return sp_g_err( 'sp_name', 'Please enter your name.' );
		}
		if ( ! is_email( $email ) ) {
			return sp_g_err( 'sp_email', 'Please enter a valid email.' );
		}
		if ( ! preg_match( '/^[6-9]\d{9}$/', $phone ) ) {
			return sp_g_err( 'sp_phone', 'Please enter a valid 10-digit WhatsApp number.' );
		}
		if ( strlen( $pass ) < 8 ) {
			return sp_g_err( 'sp_pass', 'Password needs at least 8 characters.' );
		}
		if ( email_exists( $email ) ) {
			return sp_g_err( 'sp_exists', 'This email already has an account - please log in.' );
		}
		$login = sanitize_user( strstr( $email, '@', true ), true );
		$base  = $login ? $login : 'member';
		$login = $base;
		while ( username_exists( $login ) ) {
			$login = $base . wp_rand( 100, 9999 );
		}
		$uid = wp_insert_user( array(
			'user_login'   => $login,
			'user_email'   => $email,
			'user_pass'    => $pass,
			'display_name' => $name,
			'first_name'   => $name,
			'role'         => 'subscriber',
		) );
		if ( is_wp_error( $uid ) ) {
			return sp_g_err( 'sp_fail', $uid->get_error_message() );
		}
		update_user_meta( $uid, 'sp_phone', $phone );
		update_user_meta( $uid, 'sp_points', 0 );
		$bonus = sp_g_conf()['signup_bonus'];
		if ( $bonus ) {
			sp_g_award( $uid, $bonus, 'Welcome bonus' );
		}
		wp_set_current_user( $uid );
		wp_set_auth_cookie( $uid, true, is_ssl() );
		return sp_g_me();
	} ) );

	register_rest_route( $ns, '/login', array( 'methods' => 'POST', 'permission_callback' => $open, 'callback' => function ( $req ) {
		if ( ! sp_g_throttle( 'login', 12, 15 * MINUTE_IN_SECONDS ) ) {
			return sp_g_err( 'sp_slow', 'Too many attempts. Please wait 15 minutes.', 429 );
		}
		$user = wp_signon( array(
			'user_login'    => sanitize_text_field( (string) $req->get_param( 'email' ) ),
			'user_password' => (string) $req->get_param( 'password' ),
			'remember'      => true,
		), is_ssl() );
		if ( is_wp_error( $user ) ) {
			return sp_g_err( 'sp_login', 'Email or password is not right.', 403 );
		}
		wp_set_current_user( $user->ID );
		return sp_g_me();
	} ) );

	register_rest_route( $ns, '/logout', array( 'methods' => 'POST', 'permission_callback' => $member, 'callback' => function () {
		wp_logout();
		return array( 'ok' => true );
	} ) );

	/* ten questions of a level, without answers */
	register_rest_route( $ns, '/quiz', array( 'methods' => 'GET', 'permission_callback' => $open, 'callback' => function ( $req ) {
		$conf  = sp_g_conf();
		$track = ( 'mind' === $req->get_param( 'track' ) ) ? 'mind' : 'iq';
		$level = max( 1, min( 'mind' === $track ? $conf['mind_levels'] : 10, (int) $req->get_param( 'level' ) ) );
		$uid   = get_current_user_id();
		$prog  = sp_g_progress( $uid, $track );
		if ( $level > $prog['open'] ) {
			return sp_g_err( 'sp_locked', $uid ? 'This level is still locked.' : 'Create a free account to play this level.', 403 );
		}
		$tried = $uid ? sp_g_meta( $uid, 'sp_tried', array() ) : array();
		$fresh = array();
		$old   = array();
		foreach ( sp_g_bank() as $qid => $q ) {
			if ( (int) $q['l'] !== $level || sp_g_track( $q ) !== $track ) {
				continue;
			}
			if ( isset( $tried[ $qid ] ) ) {
				$old[] = $qid;
			} else {
				$fresh[] = $qid;
			}
		}
		shuffle( $fresh );
		shuffle( $old );
		$pick = array_slice( array_merge( $fresh, $old ), 0, $conf['round'] );
		$bank = sp_g_bank();
		$out  = array();
		foreach ( $pick as $qid ) {
			$q     = $bank[ $qid ];
			$out[] = array(
				'id'    => $qid,
				'q'     => $q['q'],
				'svg'   => isset( $q['svg'] ) ? $q['svg'] : '',
				'o'     => $q['o'],
				'kind'  => $q['k'],
				'fresh' => ! isset( $tried[ $qid ] ),
			);
		}
		return array( 'level' => $level, 'track' => $track, 'questions' => $out,
			'points_each' => 'mind' === $track ? $conf['mind_points'] : $conf['per_level'][ $level ] );
	} ) );

	/* check one answer; points only for a first attempt that is right */
	register_rest_route( $ns, '/answer', array( 'methods' => 'POST', 'permission_callback' => $open, 'callback' => function ( $req ) {
		$bank   = sp_g_bank();
		$qid    = (string) $req->get_param( 'id' );
		$choice = (int) $req->get_param( 'choice' );
		if ( ! isset( $bank[ $qid ] ) ) {
			return sp_g_err( 'sp_q', 'Unknown question.' );
		}
		$q     = $bank[ $qid ];
		$right = ( (int) $q['a'] === $choice );
		$out   = array( 'correct' => $right, 'answer' => (int) $q['a'], 'explain' => $q['e'], 'awarded' => 0 );
		$uid   = get_current_user_id();
		if ( ! $uid ) {
			return $out;
		}
		$conf  = sp_g_conf();
		$level = (int) $q['l'];
		$track = sp_g_track( $q );
		if ( $level > sp_g_progress( $uid, $track )['open'] ) {
			return sp_g_err( 'sp_locked', 'This level is still locked.', 403 );
		}
		$tried = sp_g_meta( $uid, 'sp_tried', array() );
		$first = ! isset( $tried[ $qid ] );
		if ( $first ) {
			$tried[ $qid ] = 1;
			update_user_meta( $uid, 'sp_tried', $tried );
		}
		if ( $right && $first ) {
			$correct         = sp_g_meta( $uid, 'sp_correct', array() );
			$correct[ $qid ] = 1;
			update_user_meta( $uid, 'sp_correct', $correct );
			$left = sp_g_day_left( $uid );
			$give = min( $left, 'mind' === $track ? $conf['mind_points'] : $conf['per_level'][ $level ] );
			if ( $give > 0 ) {
				$today = sp_g_today();
				$used  = ( sp_g_meta( $uid, 'sp_day', '' ) === $today ) ? (int) sp_g_meta( $uid, 'sp_day_pts', 0 ) : 0;
				update_user_meta( $uid, 'sp_day', $today );
				update_user_meta( $uid, 'sp_day_pts', $used + $give );
				sp_g_award( $uid, $give, ( 'mind' === $track ? 'Mindset Challenge' : 'Brain Game' ) . ' - level ' . $level );
				$out['awarded'] = $give;
			}
		}
		$out['first']    = $first;
		$out['points']   = (int) sp_g_meta( $uid, 'sp_points', 0 );
		$out['day_left'] = sp_g_day_left( $uid );
		$out['progress'] = sp_g_progress( $uid );
		$out['progress_mind'] = sp_g_progress( $uid, 'mind' );
		return $out;
	} ) );

	register_rest_route( $ns, '/missions', array( 'methods' => 'GET', 'permission_callback' => $open, 'callback' => function () {
		return sp_g_missions();
	} ) );

	register_rest_route( $ns, '/mission', array( 'methods' => 'POST', 'permission_callback' => $member, 'callback' => function ( $req ) {
		$id   = sanitize_title( (string) $req->get_param( 'id' ) );
		$note = sanitize_textarea_field( (string) $req->get_param( 'reflection' ) );
		$hit  = null;
		foreach ( sp_g_missions()['weeks'] as $w ) {
			if ( $w['id'] === $id ) {
				$hit = $w;
			}
		}
		if ( ! $hit ) {
			return sp_g_err( 'sp_m', 'This mission is not running.' );
		}
		if ( ! $hit['open'] ) {
			return sp_g_err( 'sp_m_wait', 'This mission opens on day ' . $hit['opens'] . ' of the month.' );
		}
		if ( $hit['done'] ) {
			return sp_g_err( 'sp_m_done', 'You have already completed this mission.' );
		}
		if ( mb_strlen( $note ) < 20 ) {
			return sp_g_err( 'sp_m_note', 'Write at least a line or two about how it went.' );
		}
		$uid          = get_current_user_id();
		$done         = sp_g_meta( $uid, 'sp_missions', array() );
		$done[ $id ]  = time();
		update_user_meta( $uid, 'sp_missions', $done );
		$all = get_option( 'sp_g_reflections', array() );
		array_unshift( $all, array( 'uid' => $uid, 'name' => wp_get_current_user()->display_name, 'mission' => $hit['title'], 'id' => $id, 'note' => $note, 'at' => time() ) );
		update_option( 'sp_g_reflections', array_slice( $all, 0, 1000 ), false );
		$points = sp_g_award( $uid, $hit['points'], 'Mission - ' . $hit['title'] );
		return array( 'ok' => true, 'awarded' => $hit['points'], 'points' => $points );
	} ) );

	register_rest_route( $ns, '/redeem', array( 'methods' => 'POST', 'permission_callback' => $member, 'callback' => function ( $req ) {
		$conf   = sp_g_conf();
		$uid    = get_current_user_id();
		$item   = (string) $req->get_param( 'item' );
		$points = (int) $req->get_param( 'points' );
		$have   = (int) sp_g_meta( $uid, 'sp_points', 0 );
		if ( ! in_array( $item, $conf['items'], true ) ) {
			return sp_g_err( 'sp_item', 'Please choose what to use the points for.' );
		}
		if ( $points < $conf['min_redeem'] ) {
			return sp_g_err( 'sp_min', 'You can redeem from ' . $conf['min_redeem'] . ' points.' );
		}
		if ( $points > $have ) {
			return sp_g_err( 'sp_more', 'You have ' . $have . ' points.' );
		}
		$u    = wp_get_current_user();
		$code = 'SP-' . strtoupper( wp_generate_password( 6, false ) );
		$reqs = get_option( 'sp_g_requests', array() );
		array_unshift( $reqs, array(
			'id' => $code, 'uid' => $uid, 'name' => $u->display_name, 'email' => $u->user_email,
			'phone' => sp_g_meta( $uid, 'sp_phone', '' ), 'item' => $item, 'points' => $points,
			'status' => 'pending', 'at' => time(),
		) );
		update_option( 'sp_g_requests', array_slice( $reqs, 0, 2000 ), false );
		$left = sp_g_award( $uid, -$points, 'Redeem ' . $code . ' - ' . $item . ' (on hold)' );
		return array( 'ok' => true, 'code' => $code, 'points' => $left );
	} ) );

	/* ---- admin ---- */
	register_rest_route( $ns, '/admin/overview', array( 'methods' => 'GET', 'permission_callback' => $admin, 'callback' => function () {
		$members = count_users();
		return array(
			'requests'    => array_slice( get_option( 'sp_g_requests', array() ), 0, 100 ),
			'reflections' => array_slice( get_option( 'sp_g_reflections', array() ), 0, 60 ),
			'members'     => isset( $members['avail_roles']['subscriber'] ) ? $members['avail_roles']['subscriber'] : 0,
			'bank'        => count( sp_g_bank() ),
		);
	} ) );

	register_rest_route( $ns, '/admin/request', array( 'methods' => 'POST', 'permission_callback' => $admin, 'callback' => function ( $req ) {
		$id     = (string) $req->get_param( 'id' );
		$action = (string) $req->get_param( 'action' );
		$reqs   = get_option( 'sp_g_requests', array() );
		foreach ( $reqs as &$r ) {
			if ( $r['id'] !== $id ) {
				continue;
			}
			if ( 'pending' !== $r['status'] ) {
				return sp_g_err( 'sp_done', 'Already ' . $r['status'] . '.' );
			}
			if ( 'done' === $action ) {
				$r['status'] = 'done';
			} elseif ( 'reject' === $action ) {
				$r['status'] = 'rejected';
				sp_g_award( (int) $r['uid'], (int) $r['points'], 'Refund ' . $r['id'] );
			} else {
				return sp_g_err( 'sp_action', 'Unknown action.' );
			}
			$r['closed'] = time();
			update_option( 'sp_g_requests', $reqs, false );
			return array( 'ok' => true, 'status' => $r['status'] );
		}
		return sp_g_err( 'sp_none', 'No such request.', 404 );
	} ) );

	/* assets: the bank, the game script and its stylesheet (push_game.py) */
	register_rest_route( $ns, '/admin/assets', array( 'methods' => 'POST', 'permission_callback' => $admin, 'callback' => function ( $req ) {
		$done = array();
		$bank = $req->get_param( 'bank' );
		if ( is_array( $bank ) && count( $bank ) > 0 ) {
			update_option( 'sp_g_bank', $bank, false );
			$done[] = 'bank:' . count( $bank );
		}
		foreach ( array( 'js', 'css' ) as $k ) {
			$v = $req->get_param( $k );
			if ( is_string( $v ) && '' !== $v ) {
				update_option( 'sp_g_' . $k, $v, false );
				$done[] = $k . ':' . strlen( $v );
			}
		}
		return array( 'ok' => true, 'saved' => $done );
	} ) );
} );

/* game answers must never come out of a page cache */
add_filter( 'rest_pre_serve_request', function ( $served, $result, $request ) {
	if ( 0 === strpos( $request->get_route(), '/sp/v1' ) ) {
		do_action( 'litespeed_control_set_nocache', 'sp game' );
		nocache_headers();
	}
	return $served;
}, 10, 3 );

/* ---------------------------------------------------------------- front end */

/* the game ships in the footer of every public page, outside post content,
   so it is free of the &, <, > restrictions page 4 lives under */
add_action( 'wp_footer', function () {
	$js  = get_option( 'sp_g_js', '' );
	$css = get_option( 'sp_g_css', '' );
	if ( '' === $js ) {
		return;
	}
	echo "\n<style id=\"spg-css\">" . $css . "</style>\n"; // phpcs:ignore WordPress.Security.EscapeOutput
	echo '<script id="spg-js">window.SPG_API=' . wp_json_encode( esc_url_raw( rest_url( 'sp/v1/' ) ) ) . ';' . $js . "</script>\n"; // phpcs:ignore WordPress.Security.EscapeOutput
}, 50 );

/* a deleted member takes their reflections and requests with them */
add_action( 'deleted_user', function ( $uid ) {
	foreach ( array( 'sp_g_reflections', 'sp_g_requests' ) as $opt ) {
		$list = get_option( $opt, array() );
		$keep = array_values( array_filter( $list, function ( $r ) use ( $uid ) {
			return (int) $r['uid'] !== (int) $uid;
		} ) );
		if ( count( $keep ) !== count( $list ) ) {
			update_option( $opt, $keep, false );
		}
	}
} );

/* members are not editors: no toolbar, no dashboard */
add_filter( 'show_admin_bar', function ( $show ) {
	return current_user_can( 'edit_posts' ) ? $show : false;
} );
add_action( 'admin_init', function () {
	if ( wp_doing_ajax() || current_user_can( 'edit_posts' ) ) {
		return;
	}
	wp_safe_redirect( home_url( '/#play' ) );
	exit;
} );
