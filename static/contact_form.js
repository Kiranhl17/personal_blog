/**
 * personal_blog.html — Contact Form Fetch Integration
 * =====================================================
 * Drop this script into personal_blog.html, replacing the
 * existing handleSubmit function.
 *
 * The form POSTs JSON to /submit-contact and handles all
 * success / error states with visual feedback.
 */

async function handleSubmit(e) {
  e.preventDefault();

  const btn   = document.getElementById("submitBtn");
  const form  = e.target;

  // ── Collect field values ──────────────────────────────────────────────
  const payload = {
    name:    form.querySelector('input[type="text"]').value.trim(),
    email:   form.querySelector('input[type="email"]').value.trim(),
    subject: form.querySelector('input[name="subject"]')?.value.trim()
             ?? "Message from Portfolio",          // fallback if no subject field
    message: form.querySelector("textarea").value.trim(),
  };

  // ── Basic client-side guard ───────────────────────────────────────────
  if (!payload.name || !payload.email || !payload.message) {
    _setBtn(btn, "⚠ Please fill all fields", "#e74c3c", false);
    setTimeout(() => _resetBtn(btn), 3000);
    return;
  }

  // ── Sending state ─────────────────────────────────────────────────────
  _setBtn(btn, "Sending…", "var(--teal)", true);

  try {
    const res  = await fetch("/submit-contact", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));

    if (res.ok && data.success) {
      // ── Success ───────────────────────────────────────────────────────
      _setBtn(btn, "Message Sent! ✓", "var(--accent)", true);
      form.reset();
      _showToast("Your message is on its way to Kiran 🚀", "success");
    } else {
      // ── Server-side validation / SMTP error ───────────────────────────
      const errMsg = data.error ?? "Something went wrong. Please retry.";
      _setBtn(btn, "Failed — Retry", "#e74c3c", false);
      _showToast(errMsg, "error");
    }

  } catch (networkErr) {
    // ── Network / fetch error ─────────────────────────────────────────
    _setBtn(btn, "Network Error — Retry", "#e74c3c", false);
    _showToast("Could not reach the server. Check your connection.", "error");
  }

  // ── Reset button after 3 s ────────────────────────────────────────────
  setTimeout(() => _resetBtn(btn), 3000);
}

// ── Utility: update button appearance ────────────────────────────────────────
function _setBtn(btn, text, bg, disabled) {
  btn.textContent = text;
  btn.style.background = bg;
  btn.disabled = disabled;
}

function _resetBtn(btn) {
  btn.innerHTML = 'Send Message <i class="fas fa-paper-plane"></i>';
  btn.style.background = "var(--teal)";
  btn.disabled = false;
}

// ── Utility: toast notification ──────────────────────────────────────────────
function _showToast(message, type = "success") {
  // Remove any existing toast
  document.getElementById("contact-toast")?.remove();

  const toast = document.createElement("div");
  toast.id = "contact-toast";
  toast.textContent = message;
  Object.assign(toast.style, {
    position:     "fixed",
    bottom:       "28px",
    right:        "28px",
    padding:      "14px 22px",
    borderRadius: "10px",
    fontFamily:   "var(--font, sans-serif)",
    fontSize:     "0.9rem",
    fontWeight:   "600",
    color:        "#000",
    background:   type === "success" ? "var(--accent, #64ffda)" : "#e74c3c",
    boxShadow:    "0 8px 24px rgba(0,0,0,0.3)",
    zIndex:       "9999",
    transform:    "translateY(20px)",
    opacity:      "0",
    transition:   "transform 0.3s ease, opacity 0.3s ease",
    maxWidth:     "320px",
  });

  document.body.appendChild(toast);
  requestAnimationFrame(() => {
    toast.style.transform = "translateY(0)";
    toast.style.opacity   = "1";
  });

  setTimeout(() => {
    toast.style.transform = "translateY(20px)";
    toast.style.opacity   = "0";
    toast.addEventListener("transitionend", () => toast.remove());
  }, 4500);
}
