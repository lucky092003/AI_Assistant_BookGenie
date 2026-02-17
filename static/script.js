// ===============================
// ADD TO CART (MongoDB)
// ===============================
function addToCart(title, author, price) {
    fetch("/api/cart/add", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            title: title,
            author: author,
            price: parseFloat(price) // ensure price is float
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            updateCartCount();
            alert(`"${title}" added to cart ✅`);
        } else {
            alert("Failed to add to cart ❌");
        }
    })
    .catch(err => {
        console.error(err);
        alert("Error adding to cart ❌");
    });
}

// ===============================
// REMOVE ITEM FROM CART
// ===============================
function removeCartItem(itemId) {
    fetch("/api/cart/remove", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: itemId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Item removed from cart ✅");
            updateCartCount();
            window.location.reload(); // refresh cart page
        } else {
            alert(data.error || "Failed to remove item ❌");
        }
    })
    .catch(err => {
        console.error(err);
        alert("Error removing item ❌");
    });
}

// ===============================
// UPDATE CART COUNT
// ===============================
function updateCartCount() {
    fetch("/api/cart/count")
    .then(res => res.json())
    .then(data => {
        const cartCount = document.getElementById("cartCount");
        if(cartCount){
            cartCount.innerText = data.count;
        }
    })
    .catch(err => console.error(err));
}

// Auto update cart count on page load
document.addEventListener("DOMContentLoaded", updateCartCount);

// ===============================
// CHAT WINDOW TOGGLE
// ===============================
function toggleChat() {
    const chatWindow = document.getElementById('chatbot-container');
    if (chatWindow) {
        const isOpening = chatWindow.style.display !== 'flex';
        chatWindow.style.display = isOpening ? 'flex' : 'none';
    }
}

// ===============================
// SEND MESSAGE (TEXT + VOICE)
// ===============================
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const body = document.getElementById('chat-body');

    const text = input.value.trim();
    if (!text) return;

    // Show user message
    body.innerHTML += `<div class="message user">${text}</div>`;
    input.value = '';

    const loadingId = "load-" + Date.now();
    body.innerHTML += `<div class="message bot" id="${loadingId}">Genie thinking... 🧞‍♂️</div>`;
    body.scrollTop = body.scrollHeight;

    try {
        const response = await fetch('/api/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        const botMsg = document.getElementById(loadingId);

        if (botMsg) {
            botMsg.innerText = data.reply;

            // 🔊 AI ka reply voice me bhi
            if ('speechSynthesis' in window) {
                speakText(data.reply);
            }
        }

    } catch (error) {
        const botMsg = document.getElementById(loadingId);
        if (botMsg) botMsg.innerText = "Magic lamp flickering... Try again.";
        console.error(error);
    }

    body.scrollTop = body.scrollHeight;
}

// ===============================
// 🔊 AI VOICE REPLY FUNCTION
// ===============================
function speakText(text) {
    if (!('speechSynthesis' in window)) return;

    const speech = new SpeechSynthesisUtterance();
    speech.text = text;
    speech.lang = "en-IN";  // Hindi accent English
    speech.pitch = 1;
    speech.rate = 1;

    window.speechSynthesis.speak(speech);
}

// ===============================
// 🎤 VOICE INPUT
// ===============================
let recognition;
function startVoice() {
    if (!('webkitSpeechRecognition' in window)) {
        alert("Voice recognition not supported. Use Google Chrome.");
        return;
    }

    recognition = new webkitSpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.start();

    const micBtn = document.getElementById("voiceBtn");
    micBtn.classList.add("listening");
    micBtn.innerText = "🎙️";

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById("chatInput").value = transcript;
        sendMessage(); // text + voice reply dono
    };

    recognition.onerror = function() {
        micBtn.classList.remove("listening");
        micBtn.innerText = "🎤";
    };

    recognition.onend = function() {
        micBtn.classList.remove("listening");
        micBtn.innerText = "🎤";
    };
}
