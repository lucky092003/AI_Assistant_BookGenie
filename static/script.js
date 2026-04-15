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

    let activeChatController = null;
    let activeLoadingId = null;

// ===============================
// SEND MESSAGE
// ===============================
async function sendMessage() {
    const input = document.getElementById("chatInput");
    const body = document.getElementById("chat-body");

    if (!input || !body) return;

    const text = input.value.trim();
    if (!text) return;

    if (activeChatController) {
        activeChatController.abort();
    }
    activeChatController = new AbortController();

    body.innerHTML += `<div class="message user">${text}</div>`;
    input.value = "";

    const loadingId = "load-" + Date.now();
    activeLoadingId = loadingId;
    body.innerHTML += `<div class="message bot" id="${loadingId}">Genie thinking... 🧞‍♂️</div>`;
    body.scrollTop = body.scrollHeight;

    try {
        const response = await fetch("/api/chatbot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text }),
            signal: activeChatController.signal
        });

        const data = await response.json();
        const botMsg = document.getElementById(loadingId);

        if (botMsg) {
            if (data.stopped) {
                botMsg.innerText = "Stopped.";
            } else {
                botMsg.innerText = data.reply || "Hmm... no reply 🤔";

                if ("speechSynthesis" in window && data.reply) {
                    speakText(data.reply);
                }
            }
        }

    } catch (error) {
        const botMsg = document.getElementById(loadingId);
        if (botMsg) {
            botMsg.innerText =
                error.name === "AbortError"
                    ? "Stopped."
                    : "Magic lamp flickering... Try again ✨";
        }
    } finally {
        activeChatController = null;
        activeLoadingId = null;
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

function startVoice() {
    if (!("webkitSpeechRecognition" in window)) {
        showToast("Use Chrome for voice 🎤", false);
        return;
    }

    recognition = new webkitSpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.start();

    const micBtn = document.getElementById("voiceBtn");
    if (micBtn) {
        micBtn.classList.add("listening");
        micBtn.innerText = "🎙️";
    }

    recognition.onresult = function (event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById("chatInput").value = transcript;
        sendMessage();
    };

    recognition.onend = function () {
        if (micBtn) {
            micBtn.classList.remove("listening");
            micBtn.innerText = "🎤";
        }
    };
}

// ===============================
// STOP CHAT (TEXT + VOICE + SPEECH)
// ===============================
async function stopChat() {
    if (recognition) {
        try { recognition.stop(); } catch (e) { console.error(e); }
    }

    if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }

    if (activeChatController) {
        activeChatController.abort();
        activeChatController = null;
    }

    try {
        await fetch("/api/chatbot/stop", { method: "POST" });
    } catch (e) {
        console.error(e);
    }

    if (activeLoadingId) {
        const botMsg = document.getElementById(activeLoadingId);
        if (botMsg) botMsg.innerText = "Stopped.";
        activeLoadingId = null;
    }

    const micBtn = document.getElementById("voiceBtn");
    if (micBtn) {
        micBtn.classList.remove("listening");
        micBtn.innerText = "🎤";
    }

    showToast("Chat stopped");
}

document.addEventListener("DOMContentLoaded", function () {
    const stopBtn = document.getElementById("stopBtn");
    if (stopBtn) {
        stopBtn.addEventListener("click", stopChat);
    }
});

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