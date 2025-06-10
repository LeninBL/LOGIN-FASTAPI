document
  .getElementById("logout")
  .addEventListener("submit", async function (event) {
    event.preventDefault();

    try {
      await fetch("https://login-fastapi-9b3b.onrender.com/logout", {
        method: "POST",
        credentials: "include",
      });

      window.location.href = "/";
      if (window.location.href == "/") {
        window.location.reload();
      }
    } catch (error) {
      console.error("Error al cerrar sesión", error);
    }
  });
