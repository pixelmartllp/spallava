<?php
/**
 * SP SEO - who Shashi Pallava is, said once, for search engines and AI.
 *
 * Runs as the Code Snippets snippet "SP SEO" (published by
 * website/tools/push_seo.py; edit here, not in wp-admin).
 *
 *  - Person + ProfessionalService JSON-LD on every public page, so Google and
 *    AI answer engines connect the name, the roles and the place.
 *  - /llms.txt, generated live: a plain-text introduction for AI crawlers with
 *    the key pages and every published blog post.
 *
 * Every fact here is the owner's own (FAQ.txt, the site, his messages).
 * Location: Chandigarh, serving Punjab and clients online across India.
 */

if ( ! defined( 'ABSPATH' ) ) {
	return;
}

function sp_seo_facts() {
	return array(
		'name'     => 'Shashi Pallava',
		'roles'    => 'Life, Relationship & Mindset Coach, Mindset Mentor and Entrepreneur',
		'city'     => 'Chandigarh',
		'region'   => 'Punjab',
		'url'      => home_url( '/' ),
		'about'    => home_url( '/about-shashi-pallava/' ),
		'image'    => 'https://shashipallava.com/wp-content/uploads/2026/09/shashi-pallava-headshot.jpg',
		'logo'     => 'https://shashipallava.com/wp-content/uploads/2026/10/sp-icon-rrr-512.png',
		'phone'    => '+91-98767-32099',
		'email'    => 'shashipallava@gmail.com',
		'same_as'  => array( 'https://www.instagram.com/ShashiPallava', 'https://www.facebook.com/ShashiPallava' ),
	);
}

add_action( 'wp_head', function () {
	if ( is_admin() || is_feed() ) {
		return;
	}
	$f      = sp_seo_facts();
	$person = array(
		'@type'       => 'Person',
		'@id'         => home_url( '/#shashi' ),
		'name'        => $f['name'],
		'jobTitle'    => array( 'Life Coach', 'Relationship Coach', 'Mindset Coach', 'Mindset Mentor', 'Entrepreneur' ),
		'description' => $f['name'] . ' is a life, relationship and mindset coach, mindset mentor and entrepreneur based in ' . $f['city'] . ', ' . $f['region'] . ', who coaches women online across India in English, Hindi and Hinglish.',
		'url'         => $f['about'],
		'image'       => $f['image'],
		'email'       => $f['email'],
		'telephone'   => $f['phone'],
		'sameAs'      => $f['same_as'],
		'homeLocation' => array( '@type' => 'Place', 'name' => $f['city'] . ', ' . $f['region'] . ', India' ),
		'knowsAbout'  => array( 'Life coaching', 'Relationship coaching', 'Mindset coaching', 'Emotional well-being', 'Boundaries', 'Self-worth', 'Mindfulness', 'NLP' ),
		'hasCredential' => array( '@type' => 'EducationalOccupationalCredential', 'name' => 'Certified Life Coach',
			'recognizedBy' => array( '@type' => 'Organization', 'name' => 'Alison' ) ),
		'worksFor'    => array( '@id' => home_url( '/#coaching' ) ),
	);
	$service = array(
		'@type'       => 'ProfessionalService',
		'@id'         => home_url( '/#coaching' ),
		'name'        => $f['name'] . ' - Life, Relationship & Mindset Coaching',
		'description' => 'Online life, relationship and mindset coaching for women aged 18 to 55, by ' . $f['name'] . ', based in ' . $f['city'] . ', ' . $f['region'] . '. Free live webinar and the 6-month Revive, Rise and Relive program.',
		'url'         => $f['url'],
		'image'       => $f['image'],
		'logo'        => $f['logo'],
		'email'       => $f['email'],
		'telephone'   => $f['phone'],
		'founder'     => array( '@id' => home_url( '/#shashi' ) ),
		'address'     => array( '@type' => 'PostalAddress', 'addressLocality' => $f['city'], 'addressRegion' => $f['region'], 'addressCountry' => 'IN' ),
		'areaServed'  => array( array( '@type' => 'State', 'name' => 'Punjab' ), array( '@type' => 'City', 'name' => 'Chandigarh' ), array( '@type' => 'Country', 'name' => 'India' ) ),
		'availableLanguage' => array( 'English', 'Hindi', 'Hinglish' ),
		'sameAs'      => $f['same_as'],
	);
	$graph = array( '@context' => 'https://schema.org', '@graph' => array( $person, $service ) );
	echo "\n<script type=\"application/ld+json\" id=\"sp-entity\">" . wp_json_encode( $graph, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_HEX_TAG ) . "</script>\n"; // phpcs:ignore
}, 20 );

/* /llms.txt - a plain introduction for AI crawlers, rebuilt on every request */
add_action( 'parse_request', function () {
	$path = isset( $_SERVER['REQUEST_URI'] ) ? strtok( wp_unslash( $_SERVER['REQUEST_URI'] ), '?' ) : '';
	if ( '/llms.txt' !== $path ) {
		return;
	}
	$f     = sp_seo_facts();
	$lines = array(
		'# ' . $f['name'] . ' - ' . $f['roles'],
		'',
		'> ' . $f['name'] . ' is a life, relationship and mindset coach, mindset mentor and entrepreneur based in ' . $f['city'] . ', ' . $f['region'] . ', India. She coaches women aged 18 to 55 online, in English, Hindi and Hinglish, on mindset, confidence, emotional well-being and relationships, through coaching conversations and practical mindset tools. Certified Life Coach.',
		'',
		'## Key pages',
		'- [Home](' . $f['url'] . '): programs, free webinar registration, FAQ',
		'- [About Shashi Pallava](' . $f['about'] . '): who she is, where she is based, how she works',
		'- [Membership](' . home_url( '/membership/' ) . '): Silver, Gold and Platinum memberships',
		'- [Blog](' . home_url( '/blog/' ) . '): short reads on boundaries, relationships, healing and mindset',
		'- [Policy](' . home_url( '/policy/' ) . '): privacy and points rules',
		'',
		'## Programs',
		'- Live Webinar: free, online, open to everyone.',
		'- Revive, Rise & Relive: Rs 999, a 6-month online program - private WhatsApp community, live webinars, challenges on Mentie Go, and one personal 1:1 session. For women aged 18 to 55.',
		'- Coaching is not therapy and does not replace medical or mental health care.',
		'',
		'## Contact',
		'- WhatsApp: ' . $f['phone'],
		'- Email: ' . $f['email'],
		'- Instagram and Facebook: @ShashiPallava',
		'',
		'## Blog posts',
	);
	foreach ( get_posts( array( 'numberposts' => 200, 'post_status' => 'publish' ) ) as $p ) {
		$lines[] = '- [' . html_entity_decode( get_the_title( $p ), ENT_QUOTES, 'UTF-8' ) . '](' . get_permalink( $p ) . ')';
	}
	header( 'Content-Type: text/plain; charset=utf-8' );
	header( 'X-Robots-Tag: noindex' );
	echo implode( "\n", $lines ) . "\n"; // phpcs:ignore
	exit;
} );
