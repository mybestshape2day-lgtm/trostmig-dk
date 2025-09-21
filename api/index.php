<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <title>TrøstMig - Komplet Setup Guide</title>
    <style>
        body {
            font-family: -apple-system, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .file-box {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .filename {
            background: #7c3aed;
            color: white;
            padding: 10px;
            border-radius: 5px 5px 0 0;
            margin: -20px -20px 20px -20px;
            font-weight: bold;
        }
        pre {
            background: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        code {
            font-family: 'Monaco', monospace;
            font-size: 14px;
        }
        .success {
            background: #10b981;
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .warning {
            background: #f59e0b;
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>

<h1>🚀 KOMPLET ARBEJDENDE SETUP</h1>
<p>Her er ALLE filer du skal bruge - testet og virker!</p>

<!-- FILE 1: test-api.php -->
<div class="file-box">
    <div class="filename">📄 test-api.php (upload til /api/ mappen)</div>
    <pre><code>&lt;?php
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
?&gt;</code></pre>
</div>

<!-- FILE 2: tracker.js -->
<div class="file-box">
    <div class="filename">📄 tracker.js (upload til /api/ mappen)</div>
    <pre><code>// tracker.js - RETTET TIL TRØSTMIG.DK
// Håndterer både trøstmig.dk og xn--trstmig-r1a.dk

(function() {
    'use strict';
    
    // Auto-detect domæne og brug korrekt URL
    const currentDomain = window.location.hostname;
    const API_URL = `https://${currentDomain}/api/test-api.php`;
    
    console.log('TrøstMig Tracker - Using API:', API_URL);
    
    // Bruger ID
    let userId = localStorage.getItem('trostmig_userId');
    if (!userId) {
        userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('trostmig_userId', userId);
        
        // Opret bruger
        fetch(API_URL + '?action=createUser', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({userId: userId})
        }).then(r => r.json())
          .then(data => console.log('✅ Bruger oprettet:', data));
    }
    
    // Session tracking
    let currentSessionId = sessionStorage.getItem('trostmig_sessionId');
    
    function startSession(category) {
        fetch(API_URL + '?action=startSession', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                userId: userId,
                category: category
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                currentSessionId = data.data.sessionId;
                sessionStorage.setItem('trostmig_sessionId', currentSessionId);
                console.log('✅ Session startet:', currentSessionId);
            }
        });
    }
    
    // Daglig check-in
    function showDailyCheckIn() {
        const lastCheck = localStorage.getItem('trostmig_lastCheckIn');
        const today = new Date().toDateString();
        
        if (lastCheck === today) return;
        
        setTimeout(() => {
            const checkInDiv = document.createElement('div');
            checkInDiv.id = 'dailyCheckIn';
            checkInDiv.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: white;
                padding: 25px;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                z-index: 10000;
                max-width: 350px;
                font-family: -apple-system, sans-serif;
            `;
            
            checkInDiv.innerHTML = `
                &lt;h3 style="margin: 0 0 15px 0; color: #333;">Hvordan har du det i dag? 💜&lt;/h3>
                
                &lt;div style="margin: 15px 0;">
                    &lt;label style="display: block; margin-bottom: 5px; color: #666;">Humør (1-10)&lt;/label>
                    &lt;input type="range" id="moodScore" min="1" max="10" value="5" style="width: 100%;">
                    &lt;div style="display: flex; justify-content: space-between; font-size: 12px; color: #999;">
                        &lt;span>😔&lt;/span>
                        &lt;span id="moodValue" style="font-weight: bold;">5&lt;/span>
                        &lt;span>😊&lt;/span>
                    &lt;/div>
                &lt;/div>
                
                &lt;div style="margin: 15px 0;">
                    &lt;label style="display: block; margin-bottom: 5px; color: #666;">Energi (1-10)&lt;/label>
                    &lt;input type="range" id="energyLevel" min="1" max="10" value="5" style="width: 100%;">
                    &lt;div style="display: flex; justify-content: space-between; font-size: 12px; color: #999;">
                        &lt;span>😴&lt;/span>
                        &lt;span id="energyValue" style="font-weight: bold;">5&lt;/span>
                        &lt;span>⚡&lt;/span>
                    &lt;/div>
                &lt;/div>
                
                &lt;div style="display: flex; gap: 10px;">
                    &lt;button id="saveCheckInBtn" style="
                        flex: 1; background: #7c3aed; color: white; border: none;
                        padding: 12px; border-radius: 10px; cursor: pointer; font-size: 16px;
                    ">Gem&lt;/button>
                    &lt;button id="laterCheckInBtn" style="
                        flex: 1; background: #f0f0f0; color: #666; border: none;
                        padding: 12px; border-radius: 10px; cursor: pointer; font-size: 16px;
                    ">Senere&lt;/button>
                &lt;/div>
            `;
            
            document.body.appendChild(checkInDiv);
            
            // Event listeners
            document.getElementById('moodScore').oninput = function() {
                document.getElementById('moodValue').textContent = this.value;
            };
            document.getElementById('energyLevel').oninput = function() {
                document.getElementById('energyValue').textContent = this.value;
            };
            document.getElementById('saveCheckInBtn').onclick = saveCheckIn;
            document.getElementById('laterCheckInBtn').onclick = function() {
                checkInDiv.remove();
            };
        }, 5000); // 5 sekunder
    }
    
    function saveCheckIn() {
        const mood = document.getElementById('moodScore').value;
        const energy = document.getElementById('energyLevel').value;
        
        fetch(API_URL + '?action=checkIn', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                userId: userId,
                mood: parseInt(mood),
                energy: parseInt(energy)
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                localStorage.setItem('trostmig_lastCheckIn', new Date().toDateString());
                document.getElementById('dailyCheckIn').remove();
                showMessage('Check-in gemt! 💪');
            }
        });
    }
    
    function showMessage(text) {
        const msg = document.createElement('div');
        msg.textContent = text;
        msg.style.cssText = `
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
            background: #7c3aed; color: white; padding: 15px 25px;
            border-radius: 50px; box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            z-index: 10002;
        `;
        document.body.appendChild(msg);
        setTimeout(() => msg.remove(), 3000);
    }
    
    // Stats widget
    function showStats() {
        fetch(API_URL + '?action=getUserStats&amp;userId=' + userId)
            .then(r => r.json())
            .then(data => {
                if (!data.success) return;
                
                const stats = data.data;
                const statsDiv = document.createElement('div');
                statsDiv.innerHTML = `
                    &lt;div style="
                        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                        background: white; padding: 30px; border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3); z-index: 10001;
                        max-width: 400px; font-family: -apple-system, sans-serif;
                    ">
                        &lt;h2>Dine Fremskridt 📊&lt;/h2>
                        &lt;p>Streak: ${stats.currentStreak} dage 🔥&lt;/p>
                        &lt;p>Sessions: ${stats.totalSessions}&lt;/p>
                        &lt;p>Scripts: ${stats.totalScriptsViewed}&lt;/p>
                        &lt;button onclick="this.parentElement.remove()" style="
                            width: 100%; margin-top: 20px; background: #7c3aed;
                            color: white; border: none; padding: 15px;
                            border-radius: 10px; cursor: pointer;
                        ">Luk&lt;/button>
                    &lt;/div>
                `;
                document.body.appendChild(statsDiv.firstElementChild);
            });
    }
    
    // Init
    document.addEventListener('DOMContentLoaded', function() {
        const page = window.location.pathname.split('/').pop().replace('.html', '');
        
        if (['angst', 'depression', 'selvmord'].includes(page)) {
            startSession(page);
        }
        
        showDailyCheckIn();
        
        // Stats knap
        const statsBtn = document.createElement('button');
        statsBtn.innerHTML = '📊';
        statsBtn.style.cssText = `
            position: fixed; bottom: 80px; right: 30px; width: 50px; height: 50px;
            border-radius: 50%; background: #7c3aed; color: white; border: none;
            cursor: pointer; box-shadow: 0 5px 15px rgba(124,58,237,0.3); z-index: 1000;
        `;
        statsBtn.onclick = showStats;
        document.body.appendChild(statsBtn);
        
        console.log('✅ TrøstMig Tracker klar!');
    });
    
    window.TrostMigTracker = {
        userId: userId,
        startSession: startSession,
        showStats: showStats
    };
    
})();</code></pre>
</div>

<!-- TEST SECTION -->
<div class="file-box">
    <div class="filename">🧪 TEST TRIN</div>
    
    <h3>1. Upload begge filer til /api/ mappen</h3>
    
    <h3>2. Test API virker:</h3>
    <div class="success">
        <a href="https://trøstmig.dk/api/test-api.php?action=test" target="_blank" style="color: white;">
            https://trøstmig.dk/api/test-api.php?action=test
        </a>
    </div>
    
    <h3>3. Tilføj tracker til dine HTML sider:</h3>
    <pre><code>&lt;script src="/api/tracker.js">&lt;/script></code></pre>
    
    <h3>4. Se debug info:</h3>
    <div class="warning">
        <a href="https://trøstmig.dk/api/test-api.php?action=debug" target="_blank" style="color: white;">
            https://trøstmig.dk/api/test-api.php?action=debug
        </a>
    </div>
</div>

</body>
</html>