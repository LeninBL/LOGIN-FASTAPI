document
  .getElementById("logout")
  .addEventListener("submit", async function (event) {
    event.preventDefault();

    try {
      await fetch("https://login-fastapi-9b3b.onrender.com/logout", {
        method: "POST",
        credentials: "include",
      });

      window.location.href = "https://login-fastapi-9b3b.onrender.com/";
      if (window.location.href == "https://login-fastapi-9b3b.onrender.com/") {
        window.location.reload();
      }
    } catch (error) {
      console.error("Error al cerrar sesión", error);
    }
  });

// ======================
// 1. Interceptor de Fetch
// ======================
const originalFetch = window.fetch;
window.fetch = async function (...args) {
  const response = await originalFetch(...args);

  if (response.status === 401) {
    window.location.href = "https://login-fastapi-9b3b.onrender.com/"; // Redirige si el token expira
    return Promise.reject("Sesión expirada");
  }

  return response;
};

// ======================
// 2. Verificación Periódica
// ======================
function checkTokenValidity() {
  setInterval(async () => {
    try {
      const response = await fetch(
        "https://login-fastapi-9b3b.onrender.com/verify-token",
        {
          credentials: "include",
        }
      );
      if (!response.ok)
        window.location.href = "https://login-fastapi-9b3b.onrender.com/";
    } catch (error) {
      window.location.href = "https://login-fastapi-9b3b.onrender.com/";
    }
  }, 30000); // Chequea cada 30 segundos
}

// Iniciar cuando la página cargue
window.addEventListener("load", checkTokenValidity);

// ======================
// 3. Detección de Actividad
// ======================
["click", "mousemove", "keypress"].forEach((event) => {
  document.addEventListener(event, () => {
    fetch("/verify-token", { credentials: "include" })
      .then((response) => {
        if (!response.ok)
          window.location.href = "https://login-fastapi-9b3b.onrender.com";
      })
      .catch(
        () =>
          (window.location.href = "https://login-fastapi-9b3b.onrender.com/")
      );
  });
});
