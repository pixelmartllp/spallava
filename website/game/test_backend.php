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
echo empty( $GLOBALS['fail'] ) ? "ALL PASS\n" : "SOME FAILED\n";
