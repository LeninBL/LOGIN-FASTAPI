document
  .getElementById("logout")
  .addEventListener("submit", async function (event) {
    event.preventDefault();

    try {
      await fetch("/logout", {
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
