// TrøstMig.dk - Central TTS Configuration
// Optimeret til Chirp3-HD stemmer (som ikke understøtter pitch)

const TTS_CONFIG = {
    // INDTAST DIN API-NØGLE HER
   API_KEY: 'AIzaSyCKQO9FZXRtRtv6k_XymPXHJHp7hrvjEqk',  // <-- SKAL ændres!
    
    // HOVEDSTEMME - Charon (mandlig, dyb og rolig)
    VOICE_SETTINGS: {
        languageCode: 'da-DK',
        name: 'da-DK-Chirp3-HD-Sulafat',
        ssmlGender: 'MALE'
    },
    
    // Alternative Chirp3-HD stemmer (alle uden pitch support)
    VOICE_VARIATIONS: [
        { name: 'da-DK-Chirp3-HD-Callirrhoe', gender: 'FEMALE', description: 'Kvindelig stemme – klar tone' },
        { name: 'da-DK-Chirp3-HD-Charon', gender: 'MALE', description: 'Mandlig stemme – dyb og rolig' },
        { name: 'da-DK-Chirp3-HD-Despina', gender: 'FEMALE', description: 'Kvindelig stemme – lysere klang' },
        { name: 'da-DK-Chirp3-HD-Enceladus', gender: 'MALE', description: 'Mandlig stemme – naturlig tone' },
        { name: 'da-DK-Chirp3-HD-Erriapus', gender: 'FEMALE', description: 'Kvindelig stemme – blød tone' },
        { name: 'da-DK-Chirp3-HD-Rasalgethi', gender: 'MALE', description: 'Mandlig stemme – neutral stil' },
        { name: 'da-DK-Chirp3-HD-Sadachbia', gender: 'MALE', description: 'Mandlig stemme – rolig' },
        { name: 'da-DK-Chirp3-HD-Sadaltager', gender: 'MALE', description: 'Mandlig stemme – seriøs' },
        { name: 'da-DK-Chirp3-HD-Schedar', gender: 'MALE', description: 'Mandlig stemme – klassisk tone' },
        { name: 'da-DK-Chirp3-HD-Sulafat', gender: 'FEMALE', description: 'Kvindelig stemme – varm og behagelig' },
        { name: 'da-DK-Chirp3-HD-Umbriel', gender: 'MALE', description: 'Mandlig stemme – kraftfuld' },
        { name: 'da-DK-Chirp3-HD-Vindemiatrix', gender: 'FEMALE', description: 'Kvindelig stemme – rolig' },
        { name: 'da-DK-Chirp3-HD-Zephyr', gender: 'FEMALE', description: 'Kvindelig stemme – let og blød' }
    ],
    
    // Tale hastighed (Chirp3-HD understøtter dette)
    DEFAULT_SPEED: 0.9,  // Lidt langsommere for ro (0.25 - 4.0)
    
    // Audio settings
    AUDIO_ENCODING: 'MP3',
    
    // Cache settings
    ENABLE_CACHE: true,
    CACHE_DURATION: 7 * 24 * 60 * 60 * 1000, // 7 dage
    
    // Fallback
    USE_BROWSER_TTS_FALLBACK: false  // Sæt til true hvis du vil have browser backup
};

// Global TTS Manager klasse
class TTSManager {
    constructor() {
        this.audioCache = new Map();
        this.currentAudio = null;
        this.isPlaying = false;
        this.queue = [];
    }
    
    // Hovedfunktion: Tal tekst med Google Cloud TTS
    async speak(text, options = {}) {
        // Check om API nøgle er sat
        if (!TTS_CONFIG.API_KEY || TTS_CONFIG.API_KEY === 'DIN-GOOGLE-CLOUD-TTS-API-NØGLE-HER') {
            console.error('FEJL: Du skal indtaste din Google Cloud TTS API nøgle i tts-config.js filen!');
            if (TTS_CONFIG.USE_BROWSER_TTS_FALLBACK) {
                console.log('Bruger browser TTS som fallback...');
                return this.browserSpeak(text, options);
            }
            return;
        }
        
        try {
            // Check cache først
            const cacheKey = this.getCacheKey(text, options);
            
            if (TTS_CONFIG.ENABLE_CACHE) {
                const cached = this.getFromCache(cacheKey);
                if (cached) {
                    console.log('Afspiller fra cache');
                    return this.playAudio(cached);
                }
            }
            
            // Hent audio fra Google Cloud TTS
            console.log('Henter fra Google Cloud TTS med stemme:', TTS_CONFIG.VOICE_SETTINGS.name);
            const audioContent = await this.fetchTTS(text, options);
            
            if (audioContent) {
                // Gem i cache
                if (TTS_CONFIG.ENABLE_CACHE) {
                    this.saveToCache(cacheKey, audioContent);
                }
                
                // Afspil
                return this.playAudio(audioContent);
            }
            
        } catch (error) {
            console.error('TTS Error:', error);
            
            // Fallback til browser TTS hvis aktiveret
            if (TTS_CONFIG.USE_BROWSER_TTS_FALLBACK) {
                console.log('Falder tilbage til browser TTS');
                this.browserSpeak(text, options);
            }
        }
    }
    
    // Hent TTS fra Google Cloud (UDEN pitch for Chirp3-HD)
    async fetchTTS(text, options = {}) {
        const voice = options.voice || TTS_CONFIG.VOICE_SETTINGS;
        const speed = options.speed || TTS_CONFIG.DEFAULT_SPEED;
        // INGEN pitch variabel - Chirp3-HD understøtter det ikke
        
        const requestBody = {
            input: { text: text },
            voice: {
                languageCode: voice.languageCode,
                name: voice.name,
                ssmlGender: voice.ssmlGender
            },
            audioConfig: {
                audioEncoding: TTS_CONFIG.AUDIO_ENCODING,
                speakingRate: speed
                // INGEN pitch parameter her
            }
        };
        
        console.log('Sender request til Google med voice:', voice.name);
        
        const response = await fetch(`https://texttospeech.googleapis.com/v1/text:synthesize?key=${TTS_CONFIG.API_KEY}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorData = await response.text();
            throw new Error(`Google TTS API error: ${response.status} - ${errorData}`);
        }
        
        const data = await response.json();
        return data.audioContent;
    }
    
    // Afspil audio
    playAudio(base64Audio) {
        return new Promise((resolve, reject) => {
            // Stop current audio hvis det spiller
            if (this.currentAudio) {
                this.currentAudio.pause();
                this.currentAudio = null;
            }
            
            const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
            this.currentAudio = audio;
            
            audio.onended = () => {
                this.isPlaying = false;
                this.currentAudio = null;
                resolve();
            };
            
            audio.onerror = (error) => {
                this.isPlaying = false;
                this.currentAudio = null;
                reject(error);
            };
            
            audio.play();
            this.isPlaying = true;
        });
    }
    
    // Browser TTS fallback
    browserSpeak(text, options = {}) {
        if (!('speechSynthesis' in window)) {
            console.error('Browser understøtter ikke TTS');
            return;
        }
        
        window.speechSynthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'da-DK';
        utterance.rate = options.speed || 0.9;
        utterance.volume = 0.9;
        
        // Find dansk stemme hvis mulig
        const voices = window.speechSynthesis.getVoices();
        const danishVoice = voices.find(voice => voice.lang.includes('da'));
        if (danishVoice) {
            utterance.voice = danishVoice;
            console.log('Bruger browser stemme:', danishVoice.name);
        }
        
        window.speechSynthesis.speak(utterance);
    }
    
    // Pause/Resume
    pause() {
        if (this.currentAudio && this.isPlaying) {
            this.currentAudio.pause();
            this.isPlaying = false;
        } else if ('speechSynthesis' in window) {
            window.speechSynthesis.pause();
        }
    }
    
    resume() {
        if (this.currentAudio && !this.isPlaying) {
            this.currentAudio.play();
            this.isPlaying = true;
        } else if ('speechSynthesis' in window) {
            window.speechSynthesis.resume();
        }
    }
    
    stop() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
            this.isPlaying = false;
        }
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    }
    
    // Cache funktioner
    getCacheKey(text, options) {
        const keyString = text.substring(0, 20) + JSON.stringify(options);
        return btoa(encodeURIComponent(keyString)).replace(/[^a-zA-Z0-9]/g, '').substring(0, 50);
    }
    
    getFromCache(key) {
        try {
            const cached = localStorage.getItem(`tts_cache_${key}`);
            if (cached) {
                const data = JSON.parse(cached);
                if (Date.now() - data.timestamp < TTS_CONFIG.CACHE_DURATION) {
                    return data.audio;
                }
                localStorage.removeItem(`tts_cache_${key}`);
            }
        } catch (e) {
            console.error('Cache error:', e);
        }
        return null;
    }
    
    saveToCache(key, audioContent) {
        try {
            const data = {
                audio: audioContent,
                timestamp: Date.now()
            };
            localStorage.setItem(`tts_cache_${key}`, JSON.stringify(data));
        } catch (e) {
            console.warn('Could not cache audio:', e);
            this.clearOldCache();
        }
    }
    
    clearOldCache() {
        const keys = Object.keys(localStorage);
        const ttsKeys = keys.filter(k => k.startsWith('tts_cache_'));
        
        // Slet de ældste 10 entries
        ttsKeys.slice(0, 10).forEach(key => {
            localStorage.removeItem(key);
        });
    }
    
    // Clear all cache
    clearAllCache() {
        const keys = Object.keys(localStorage);
        const ttsKeys = keys.filter(k => k.startsWith('tts_cache_'));
        ttsKeys.forEach(key => {
            localStorage.removeItem(key);
        });
        console.log(`Ryddede ${ttsKeys.length} cache entries`);
    }
}

// Opret global TTS instance
const TTS = new TTSManager();

// Hjælpe funktioner til nem brug
function speak(text, options = {}) {
    return TTS.speak(text, options);
}

// Emotions uden pitch (kun hastighed for Chirp3-HD)
function speakWithEmotion(text, emotion = 'calm') {
    const emotions = {
        calm: { speed: 0.85 },      // Rolig og langsom
        happy: { speed: 1.0 },       // Normal hastighed
        serious: { speed: 0.8 },     // Meget langsom og alvorlig
        encouraging: { speed: 0.95 } // Næsten normal
    };
    
    return TTS.speak(text, emotions[emotion] || emotions.calm);
}

function speakSequence(texts, delay = 1000) {
    let promise = Promise.resolve();
    
    texts.forEach((text, index) => {
        promise = promise.then(() => {
            return TTS.speak(text);
        }).then(() => {
            if (index < texts.length - 1) {
                return new Promise(resolve => setTimeout(resolve, delay));
            }
        });
    });
    
    return promise;
}

// Auto-start når en side loader
document.addEventListener('DOMContentLoaded', () => {
    // Log current settings
    console.log('TTS Config loaded:');
    console.log('- Stemme:', TTS_CONFIG.VOICE_SETTINGS.name);
    console.log('- API nøgle sat:', TTS_CONFIG.API_KEY !== 'DIN-GOOGLE-CLOUD-TTS-API-NØGLE-HER' ? 'Ja' : 'NEJ - SKAL SÆTTES!');
    
    // Tjek om siden har en velkomst-besked
    const welcomeElement = document.querySelector('[data-tts-welcome]');
    if (welcomeElement) {
        const text = welcomeElement.getAttribute('data-tts-welcome');
        setTimeout(() => speak(text), 1000);
    }
    
    // Gør alle elementer med data-tts klikbare
    document.querySelectorAll('[data-tts]').forEach(element => {
        element.style.cursor = 'pointer';
        element.addEventListener('click', () => {
            const text = element.getAttribute('data-tts') || element.textContent;
            speak(text);
        });
    });
});

// Export til brug i andre scripts
window.TrøstMigTTS = {
    speak,
    speakWithEmotion,
    speakSequence,
    pause: () => TTS.pause(),
    resume: () => TTS.resume(),
    stop: () => TTS.stop(),
    clearCache: () => TTS.clearAllCache(),
    getVoices: () => TTS_CONFIG.VOICE_VARIATIONS,
    getCurrentVoice: () => TTS_CONFIG.VOICE_SETTINGS.name,
    setVoice: (voiceIndex) => {
        if (voiceIndex < TTS_CONFIG.VOICE_VARIATIONS.length) {
            TTS_CONFIG.VOICE_SETTINGS = {
                languageCode: 'da-DK',
                name: TTS_CONFIG.VOICE_VARIATIONS[voiceIndex].name,
                ssmlGender: TTS_CONFIG.VOICE_VARIATIONS[voiceIndex].gender
            };
            console.log('Skiftet til stemme:', TTS_CONFIG.VOICE_SETTINGS.name);
        }
    },
    testConnection: async () => {
        try {
            await speak('Test af Charon stemmen');
            console.log('✓ TTS virker med Google Cloud!');
            return true;
        } catch (e) {
            console.error('✗ TTS fejlede:', e);
            return false;
        }
    }
};

console.log('TrøstMig TTS loaded. Test med: TrøstMigTTS.testConnection()');