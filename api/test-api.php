<?php
// test-api.php - VIRKER UDEN DATABASE!
// Bruger session til at gemme data midlertidigt

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle OPTIONS request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// Start session
session_start();

// Initialiser session arrays
if (!isset($_SESSION['users'])) $_SESSION['users'] = [];
if (!isset($_SESSION['sessions'])) $_SESSION['sessions'] = [];
if (!isset($_SESSION['checkins'])) $_SESSION['checkins'] = [];
if (!isset($_SESSION['stats'])) $_SESSION['stats'] = [];

$action = $_GET['action'] ?? '';
$method = $_SERVER['REQUEST_METHOD'];

switch($action) {
    
    case 'test':
        success([
            'message' => '✅ API virker perfekt!',
            'domain' => $_SERVER['HTTP_HOST'],
            'php_version' => phpversion(),
            'time' => date('Y-m-d H:i:s')
        ]);
        break;
    
    case 'createUser':
        $input = json_decode(file_get_contents('php://input'), true);
        $userId = $input['userId'] ?? 'user_' . uniqid();
        
        $_SESSION['users'][$userId] = [
            'created' => time(),
            'lastLogin' => time(),
            'name' => $input['name'] ?? 'Anonym'
        ];
        
        success([
            'userId' => $userId,
            'message' => 'Bruger oprettet!'
        ]);
        break;
    
    case 'startSession':
        $input = json_decode(file_get_contents('php://input'), true);
        $sessionId = 'session_' . uniqid();
        
        $_SESSION['sessions'][$sessionId] = [
            'userId' => $input['userId'] ?? '',
            'category' => $input['category'] ?? 'general',
            'started' => time(),
            'scripts' => 0
        ];
        
        success(['sessionId' => $sessionId]);
        break;
    
    case 'updateProgress':
        $input = json_decode(file_get_contents('php://input'), true);
        $sessionId = $input['sessionId'] ?? '';
        
        if (isset($_SESSION['sessions'][$sessionId])) {
            $_SESSION['sessions'][$sessionId]['scripts']++;
            $_SESSION['sessions'][$sessionId]['lastUpdate'] = time();
        }
        
        success(['message' => 'Progress opdateret']);
        break;
    
    case 'checkIn':
        $input = json_decode(file_get_contents('php://input'), true);
        $userId = $input['userId'] ?? '';
        
        $checkIn = [
            'userId' => $userId,
            'mood' => $input['mood'] ?? 5,
            'energy' => $input['energy'] ?? 5,
            'notes' => $input['notes'] ?? '',
            'date' => date('Y-m-d')
        ];
        
        $_SESSION['checkins'][] = $checkIn;
        
        // Opdater streak
        $streak = 1;
        $dates = array_column($_SESSION['checkins'], 'date');
        $uniqueDates = array_unique($dates);
        $streak = count($uniqueDates);
        
        success([
            'message' => 'Check-in gemt!',
            'streak' => $streak
        ]);
        break;
    
    case 'getUserStats':
        $userId = $_GET['userId'] ?? '';
        
        // Beregn stats fra session
        $userSessions = array_filter($_SESSION['sessions'], function($s) use ($userId) {
            return $s['userId'] === $userId;
        });
        
        $userCheckins = array_filter($_SESSION['checkins'], function($c) use ($userId) {
            return $c['userId'] === $userId;
        });
        
        $totalScripts = array_sum(array_column($userSessions, 'scripts'));
        $uniqueDates = count(array_unique(array_column($userCheckins, 'date')));
        
        success([
            'totalSessions' => count($userSessions),
            'currentStreak' => $uniqueDates,
            'totalScriptsViewed' => $totalScripts,
            'daysActive' => $uniqueDates
        ]);
        break;
    
    case 'debug':
        success([
            'users' => count($_SESSION['users']),
            'sessions' => count($_SESSION['sessions']),
            'checkins' => count($_SESSION['checkins']),
            'data' => $_SESSION
        ]);
        break;
    
    default:
        error('Ukendt handling: ' . $action);
}

function success($data) {
    echo json_encode(['success' => true, 'data' => $data]);
    exit;
}

function error($msg) {
    echo json_encode(['success' => false, 'error' => $msg]);
    exit;
}
?>