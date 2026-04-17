// ===============================
// ADD TO CART (Guest + Logged-in)
// ===============================
async function addToCart(title) {
    try {
        const response = await fetch("/api/cart/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title })
        });

        const data = await response.json();

        if (data.success) {
            updateCartCount();
            showToast(`"${title}" added to cart ✅`);
        } else {
            showToast(data.error || "Failed to add ❌", false);
        }

    } catch (err) {
        console.error(err);
        showToast("Server error ❌", false);
    }
}

// ===============================
// REMOVE ITEM (No Reload)
// ===============================
async function removeCartItem(itemId) {
    try {
        const response = await fetch("/api/cart/remove", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: itemId })
        });

        const data = await response.json();

        if (data.success) {
            showToast("Item removed ✅");
            updateCartCount();

            // Remove row without reload
            const row = document.querySelector(`[data-id="${itemId}"]`);
            if (row) row.remove();

            recalculateTotal();

        } else {
            showToast(data.error || "Failed ❌", false);
        }

    } catch (err) {
        console.error(err);
        showToast("Error removing ❌", false);
    }
}

// ===============================
// BUY CART (Login Only)
// ===============================
async function buyCart() {
    try {
        const response = await fetch("/api/cart/buy", {
            method: "POST"
        });

        const data = await response.json();

        if (response.status === 401) {
            showToast("Please login to continue 🔐", false);
            setTimeout(() => {
                window.location.href = "/login";
            }, 1500);
            return;
        }

        if (data.success) {
            showToast("Order placed successfully 🎉");
            updateCartCount();
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showToast(data.message || "Failed to place order ❌", false);
        }

    } catch (err) {
        console.error(err);
        showToast("Server error ❌", false);
    }
}

// ===============================
// CLEAR CART
// ===============================
async function clearCart() {
    try {
        const res = await fetch("/api/cart/clear", { method: "POST" });
        const data = await res.json();

        if (data.success) {
            showToast("Cart cleared ✅");
            updateCartCount();
            setTimeout(() => window.location.reload(), 1200);
        }

    } catch (err) {
        console.error(err);
        showToast("Failed ❌", false);
    }
}

// ===============================
// UPDATE CART COUNT
// ===============================
async function updateCartCount() {
    try {
        const response = await fetch("/api/cart/count");
        const data = await response.json();

        const cartCount = document.getElementById("cartCount");
        if (cartCount) {
            cartCount.innerText = data.count || 0;
        }

    } catch (err) {
        console.error(err);
    }
}

document.addEventListener("DOMContentLoaded", updateCartCount);

// ===============================
// CHAT AUDIO CONTROLS
// ===============================
let speakerEnabled = false;
let isListening = false;
let micAlwaysOn = false;

// ===============================
// RECALCULATE TOTAL (Without Reload)
// ===============================
function recalculateTotal() {
    const priceElements = document.querySelectorAll(".cart-details .price");
    let total = 0;

    priceElements.forEach(el => {
        const value = parseFloat(el.innerText.replace(/[^\d.]/g, ""));
        total += value;
    });

    const totalEl = document.querySelector(".cart-total h2");
    if (totalEl) {
        totalEl.innerText = "Total: ₹" + total;
    }
}

// ===============================
// CHAT WINDOW
// ===============================
function toggleChat() {
    const chatWindow = document.getElementById("chatbot-container");
    if (!chatWindow) return;

    chatWindow.style.display =
        chatWindow.style.display === "flex" ? "none" : "flex";
}

// ===============================
// SEND MESSAGE
// ===============================
async function sendMessage() {
    const input = document.getElementById("chatInput");
    const body = document.getElementById("chat-body");

    if (!input || !body) return;

    const text = input.value.trim();
    if (!text) return;

    body.innerHTML += `<div class="message user">${text}</div>`;
    input.value = "";

    const loadingId = "load-" + Date.now();
    body.innerHTML += `<div class="message bot" id="${loadingId}">Genie thinking... 🧞‍♂️</div>`;
    body.scrollTop = body.scrollHeight;

    try {
        const response = await fetch("/api/chatbot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        const botMsg = document.getElementById(loadingId);

        if (botMsg) {
            botMsg.innerText = data.reply || "Hmm... no reply 🤔";

            if (speakerEnabled && "speechSynthesis" in window && data.reply) {
                speakText(data.reply);
            }
        }

    } catch (error) {
        const botMsg = document.getElementById(loadingId);
        if (botMsg) botMsg.innerText = "Magic lamp flickering... Try again ✨";
    }

    body.scrollTop = body.scrollHeight;
}

// ===============================
// VOICE REPLY
// ===============================
function speakText(text) {
    if (!("speechSynthesis" in window)) return;

    const speech = new SpeechSynthesisUtterance(text);
    speech.lang = "en-IN";
    speech.pitch = 1;
    speech.rate = 1;

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(speech);
}

// ===============================
// VOICE INPUT
// ===============================
let recognition;

function getSpeechRecognition() {
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function updateAudioButtonState() {
    const voiceBtn = document.getElementById("voiceBtn");
    const speakerToggleBtn = document.getElementById("speakerToggleBtn");

    if (voiceBtn) {
        voiceBtn.classList.toggle("is-on", isListening);
        voiceBtn.classList.toggle("is-off", !isListening);
        voiceBtn.classList.toggle("listening", isListening);
        voiceBtn.title = isListening ? "Mic is on. Tap to stop." : "Mic is off";
        voiceBtn.innerText = isListening ? "🎙️" : "🎤";
    }

    if (speakerToggleBtn) {
        speakerToggleBtn.classList.toggle("is-on", speakerEnabled);
        speakerToggleBtn.classList.toggle("is-off", !speakerEnabled);
        speakerToggleBtn.title = speakerEnabled ? "Speaker is on" : "Speaker is off";
        speakerToggleBtn.innerText = speakerEnabled ? "🔊" : "🔈";
    }
}

function toggleSpeaker() {
    speakerEnabled = !speakerEnabled;
    updateAudioButtonState();

    if (!speakerEnabled && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }

    showToast(speakerEnabled ? "Speaker enabled" : "Speaker disabled", speakerEnabled);
}

function toggleVoiceInput() {
    if (micAlwaysOn) {
        micAlwaysOn = false;
        if (recognition) {
            recognition.stop();
        }
        isListening = false;
        updateAudioButtonState();
        showToast("Mic turned off", false);
        return;
    }

    micAlwaysOn = true;
    showToast("Mic turned on. I am listening.", true);
    startVoice();
}

function startVoice() {
    const SpeechRecognitionAPI = getSpeechRecognition();
    if (!SpeechRecognitionAPI) {
        showToast("Voice input not supported in this browser.", false);
        return;
    }

    if (recognition) {
        recognition.stop();
    }

    recognition = new SpeechRecognitionAPI();
    recognition.lang = "en-IN";
    recognition.continuous = true;
    recognition.interimResults = false;

    isListening = true;
    updateAudioButtonState();

    recognition.start();

    recognition.onresult = function (event) {
        const transcript = event?.results?.[0]?.[0]?.transcript || "";
        if (!transcript) {
            showToast("Could not hear clearly. Please try again.", false);
            return;
        }

        const input = document.getElementById("chatInput");
        if (input) {
            input.value = transcript;
        }
        sendMessage();
    };

    recognition.onerror = function (event) {
        const errorMessage = event?.error || "voice-error";
        if (errorMessage === "not-allowed") {
            showToast("Microphone permission denied. Please allow mic access.", false);
        } else if (errorMessage === "no-speech") {
            showToast("No speech detected. Please try again.", false);
        } else {
            showToast("Voice error: " + errorMessage, false);
        }
    };

    recognition.onend = function () {
        if (micAlwaysOn) {
            setTimeout(() => {
                if (micAlwaysOn) {
                    startVoice();
                }
            }, 150);
            return;
        }

        isListening = false;
        updateAudioButtonState();
    };
}

document.addEventListener("DOMContentLoaded", updateAudioButtonState);

// ===============================
// TOAST SYSTEM (Improved)
// ===============================
function showToast(message, success = true) {

    const existing = document.querySelector(".toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = success ? "toast success" : "toast error";
    toast.innerText = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}