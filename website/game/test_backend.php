<?php
// Offline tests of the money logic in sp-game.php, with WordPress stubbed out.
// Run: php website/game/test_backend.php   (expects ALL PASS)
// Minimal WordPress stand-ins to exercise sp-game.php's money logic offline.
define( 'ABSPATH', '/' );
define( 'HOUR_IN_SECONDS', 3600 );
define( 'MINUTE_IN_SECONDS', 60 );
$GLOBALS['routes'] = array();
$GLOBALS['meta']   = array();
$GLOBALS['opts']   = array( 'sp_g_bank' => json_decode( file_get_contents( __DIR__ . '/bank.json' ), true ) );
$GLOBALS['uid']    = 0;
$GLOBALS['today']  = '2026-10-13';
function add_action( $h, $cb, $p = 10, $n = 1 ) { if ( 'rest_api_init' === $h ) { $cb(); } }
function add_filter() {}
function register_rest_route( $ns, $r, $a ) { $GLOBALS['routes'][ $r ] = $a['callback']; }
function get_option( $k, $d = false ) { return isset( $GLOBALS['opts'][ $k ] ) ? $GLOBALS['opts'][ $k ] : $d; }
function update_option( $k, $v ) { $GLOBALS['opts'][ $k ] = $v; }
function get_user_meta( $u, $k, $s ) { return isset( $GLOBALS['meta'][ $u ][ $k ] ) ? $GLOBALS['meta'][ $u ][ $k ] : ''; }
function update_user_meta( $u, $k, $v ) { $GLOBALS['meta'][ $u ][ $k ] = $v; }
function get_current_user_id() { return $GLOBALS['uid']; }
function is_user_logged_in() { return (bool) $GLOBALS['uid']; }
function current_user_can() { return false; }
function wp_date( $f ) { return 'j' === $f ? '13' : $GLOBALS['today']; }
function wp_get_current_user() { return (object) array( 'display_name' => 'T', 'user_email' => 't@x', 'user_registered' => '2026-10-13 10:00:00' ); }
function wp_generate_password( $n ) { return substr( md5( mt_rand() ), 0, $n ); }
function delete_user_meta( $u, $k ) { unset( $GLOBALS['meta'][ $u ][ $k ] ); }
function get_page_by_path( $p ) { return isset( $GLOBALS['page'] ) ? $GLOBALS['page'] : null; }
function wp_strip_all_tags( $s ) { return strip_tags( $s ); }
function sanitize_title( $s ) { return trim( preg_replace( '/[^a-z0-9]+/', '-', strtolower( $s ) ), '-' ); }
function sanitize_textarea_field( $s ) { return trim( $s ); }
function sanitize_text_field( $s ) { return trim( $s ); }
function is_wp_error( $x ) { return $x instanceof WP_Error; }
$GLOBALS['tr'] = array();
function get_transient( $k ) { return isset( $GLOBALS['tr'][ $k ] ) ? $GLOBALS['tr'][ $k ] : false; }
function set_transient( $k, $v ) { $GLOBALS['tr'][ $k ] = $v; }
class WP_Error { public $c; public $m; function __construct( $c, $m ) { $this->c = $c; $this->m = $m; } }
class Req { public $p; function __construct( $p ) { $this->p = $p; } function get_param( $k ) { return isset( $this->p[ $k ] ) ? $this->p[ $k ] : null; } }
$code = file_get_contents( __DIR__ . '/sp-game.php' );
eval( '?>' . $code );

function call( $r, $p = array() ) { return $GLOBALS['routes'][ $r ]( new Req( $p ) ); }
function ok( $label, $cond ) { echo ( $cond ? 'PASS ' : 'FAIL ' ) . $label . "\n"; if ( ! $cond ) { $GLOBALS['fail'] = 1; } }
$bank = $GLOBALS['opts']['sp_g_bank'];

// guest
$q = call( '/quiz', array( 'level' => 1, 'track' => 'mind' ) );
ok( 'guest gets 10 mindset L1 questions, all track mind', 10 === count( $q['questions'] ) && 0 === strpos( $q['questions'][0]['id'], 'M01' ) );
ok( 'guest blocked from mindset L2', call( '/quiz', array( 'level' => 2, 'track' => 'mind' ) ) instanceof WP_Error );
ok( 'guest IQ L2 allowed', ! ( call( '/quiz', array( 'level' => 2 ) ) instanceof WP_Error ) );
ok( 'answers never in quiz payload', ! isset( $q['questions'][0]['a'] ) );

// member
$GLOBALS['uid'] = 7;
$mindL1 = array_keys( array_filter( $bank, function ( $x ) { return isset( $x['tr'] ) && 'mind' === $x['tr'] && 1 === $x['l']; } ) );
$r = call( '/answer', array( 'id' => $mindL1[0], 'choice' => $bank[ $mindL1[0] ]['a'] ) );
ok( 'mindset right answer pays mind_points (2)', 2 === $r['awarded'] && 2 === $r['points'] );
$r = call( '/answer', array( 'id' => $mindL1[0], 'choice' => $bank[ $mindL1[0] ]['a'] ) );
ok( 'same question again pays 0', 0 === $r['awarded'] );
$wrongFirst = $mindL1[1];
call( '/answer', array( 'id' => $wrongFirst, 'choice' => ( $bank[ $wrongFirst ]['a'] + 1 ) % 4 ) );
$r = call( '/answer', array( 'id' => $wrongFirst, 'choice' => $bank[ $wrongFirst ]['a'] ) );
ok( 'wrong first try, then right, pays 0', 0 === $r['awarded'] );
ok( 'mindset L2 still locked', call( '/quiz', array( 'level' => 2, 'track' => 'mind' ) ) instanceof WP_Error );
foreach ( array_slice( $mindL1, 2, 7 ) as $id ) { call( '/answer', array( 'id' => $id, 'choice' => $bank[ $id ]['a'] ) ); }
$p = sp_g_progress( 7, 'mind' );
ok( 'after 8 right, mindset L2 opens (correct=' . $p['correct'][1] . ', open=' . $p['open'] . ')', 2 === $p['open'] );
ok( 'IQ progress unaffected by mindset', 1 === sp_g_progress( 7 )['open'] );
// daily cap: points so far 2*8 = 16; play IQ L1 (1 each) up to cap 30
$iqL1 = array_keys( array_filter( $bank, function ( $x ) { return 'iq' === $x['tr'] && 1 === $x['l']; } ) );
foreach ( array_slice( $iqL1, 0, 40 ) as $id ) { $r = call( '/answer', array( 'id' => $id, 'choice' => $bank[ $id ]['a'] ) ); }
ok( 'daily cap holds at 30 (day_left=' . $r['day_left'] . ', points=' . $r['points'] . ')', 0 === $r['day_left'] && 30 === $r['points'] );
$GLOBALS['today'] = '2026-10-14';
$r = call( '/answer', array( 'id' => $iqL1[45], 'choice' => $bank[ $iqL1[45] ]['a'] ) );
ok( 'next day pays again', 1 === $r['awarded'] );
// redeem minimum
ok( 'redeem below 100 refused', call( '/redeem', array( 'item' => 'Gold membership', 'points' => 60 ) ) instanceof WP_Error );
ok( 'unknown item refused', call( '/redeem', array( 'item' => 'Diamond', 'points' => 100 ) ) instanceof WP_Error );
$GLOBALS['meta'][7]['sp_points'] = 150;
$r = call( '/redeem', array( 'item' => 'Silver membership', 'points' => 100 ) );
ok( 'redeem 100 of 150 leaves 50', is_array( $r ) && 50 === $r['points'] );
ok( 'redeem more than balance refused', call( '/redeem', array( 'item' => 'Silver membership', 'points' => 100 ) ) instanceof WP_Error );
$me = sp_g_me();
ok( 'me has both tracks and joined date', isset( $me['progress_mind']['levels'] ) && 5 === $me['progress_mind']['levels'] && $me['joined'] );

// phone numbers carry a country code
ok( 'India number gets +91', '+91 9876543210' === sp_g_phone( '91', '98765 43210' ) );
ok( 'India number typed with 91 in front', '+91 9876543210' === sp_g_phone( '+91', '919876543210' ) );
ok( 'India number must be 10 digits from 6-9', sp_g_phone( '91', '5876543210' ) instanceof WP_Error );
ok( 'UK number accepted, trunk zero dropped', '+44 7911123456' === sp_g_phone( '44', '07911 123456' ) );
ok( 'India number with a leading 0', '+91 9876543210' === sp_g_phone( '91', '09876543210' ) );
ok( 'too short refused', sp_g_phone( '1', '123' ) instanceof WP_Error );

// missions: buttons for everyone, the inside only for paid members
$GLOBALS['page'] = (object) array( 'post_status' => 'publish', 'post_content' => '<p>' . str_replace( "\n", '</p><p>', trim( file_get_contents( __DIR__ . '/missions.txt' ) ) ) . '</p>' );
$m = call( '/missions' );
ok( 'non-member sees Mission 1..4 buttons', 4 === count( $m['weeks'] ) && 'Mission 1' === $m['weeks'][0]['label'] && ! $m['member'] );
ok( 'non-member gets no mission text', ! isset( $m['weeks'][0]['title'] ) && ! isset( $m['weeks'][0]['desc'] ) && $m['weeks'][0]['locked'] );
ok( 'non-member cannot complete a mission', call( '/mission', array( 'id' => $m['weeks'][0]['id'], 'reflection' => str_repeat( 'x', 30 ) ) ) instanceof WP_Error );
$GLOBALS['meta'][7]['sp_plan'] = 'gold';
$GLOBALS['meta'][7]['sp_plan_until'] = '2026-10-13';
ok( 'plan that ended yesterday is not active', ! sp_g_plan( 7 )['active'] );
$GLOBALS['meta'][7]['sp_plan_until'] = '';
$m = call( '/missions' );
ok( 'member sees the mission text', $m['member'] && isset( $m['weeks'][0]['title'] ) && ! $m['weeks'][0]['locked'] );
$before = (int) $GLOBALS['meta'][7]['sp_points'];
$r = call( '/mission', array( 'id' => $m['weeks'][0]['id'], 'reflection' => 'I said no to one request and felt calm after.' ) );
ok( 'member completes mission 1 and is paid', is_array( $r ) && $r['awarded'] === $m['weeks'][0]['points'] && $r['points'] === $before + $r['awarded'] );
ok( 'same mission twice refused', call( '/mission', array( 'id' => $m['weeks'][0]['id'], 'reflection' => 'Again, trying for points twice.' ) ) instanceof WP_Error );
ok( 'me says member with plan Gold', sp_g_me()['member'] && 'Gold' === sp_g_me()['plan'] );
echo empty( $GLOBALS['fail'] ) ? "ALL PASS\n" : "SOME FAILED\n";
