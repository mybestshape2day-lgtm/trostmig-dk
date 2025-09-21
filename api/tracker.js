// tracker.js - RETTET TIL TRØSTMIG.DK
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
                <h3 style="margin: 0 0 15px 0; color: #333;">Hvordan har du det i dag? 💜</h3>
                
                <div style="margin: 15px 0;">
                    <label style="display: block; margin-bottom: 5px; color: #666;">Humør (1-10)</label>
                    <input type="range" id="moodScore" min="1" max="10" value="5" style="width: 100%;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #999;">
                        <span>😔</span>
                        <span id="moodValue" style="font-weight: bold;">5</span>
                        <span>😊</span>
                    </div>
                </div>
                
                <div style="margin: 15px 0;">
                    <label style="display: block; margin-bottom: 5px; color: #666;">Energi (1-10)</label>
                    <input type="range" id="energyLevel" min="1" max="10" value="5" style="width: 100%;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #999;">
                        <span>😴</span>
                        <span id="energyValue" style="font-weight: bold;">5</span>
                        <span>⚡</span>
                    </div>
                </div>
                
                <div style="display: flex; gap: 10px;">
                    <button id="saveCheckInBtn" style="
                        flex: 1; background: #7c3aed; color: white; border: none;
                        padding: 12px; border-radius: 10px; cursor: pointer; font-size: 16px;
                    ">Gem</button>
                    <button id="laterCheckInBtn" style="
                        flex: 1; background: #f0f0f0; color: #666; border: none;
                        padding: 12px; border-radius: 10px; cursor: pointer; font-size: 16px;
                    ">Senere</button>
                </div>
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
        fetch(API_URL + '?action=getUserStats&userId=' + userId)
            .then(r => r.json())
            .then(data => {
                if (!data.success) return;
                
                const stats = data.data;
                const statsDiv = document.createElement('div');
                statsDiv.innerHTML = `
                    <div style="
                        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                        background: white; padding: 30px; border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3); z-index: 10001;
                        max-width: 400px; font-family: -apple-system, sans-serif;
                    ">
                        <h2>Dine Fremskridt 📊</h2>
                        <p>Streak: ${stats.currentStreak} dage 🔥</p>
                        <p>Sessions: ${stats.totalSessions}</p>
                        <p>Scripts: ${stats.totalScriptsViewed}</p>
                        <button onclick="this.parentElement.remove()" style="
                            width: 100%; margin-top: 20px; background: #7c3aed;
                            color: white; border: none; padding: 15px;
                            border-radius: 10px; cursor: pointer;
                        ">Luk</button>
                    </div>
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
    
})();