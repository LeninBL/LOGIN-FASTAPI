async function isSessionValid() {
  const response = await fetch(
    "https://login-fastapi-9b3b.onrender.com/verify-token",
    {
      credentials: "include", // Necesario para que se envíen las cookies
    }
  );

  return response.ok;
}
async function createUser() {
  const sessionIsValid = await isSessionValid();
  if (!sessionIsValid) {
    alert("Tu sesión ha expirado. Por favor, vuelve a iniciar sesión.");
    window.location.href = "https://login-fastapi-9b3b.onrender.com/"; // O redirige a la página de login
    return;
  }

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("new-password").value;
  const confirmPassword = document.getElementById("confirm-password").value;

  if (!username || !password || !confirmPassword) {
    alert("Por favor, completa todos los campos.");
    return;
  }

  if (password !== confirmPassword) {
    alert("Las contraseñas no coinciden.");
    return;
  }

  const user = {
    username: username,
    hashed_password: password,
  };

  fetch("https://login-fastapi-9b3b.onrender.com/users/me/create", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include", // Esto envía las cookies
    body: JSON.stringify(user),
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((err) => {
          throw new Error(err.detail || "Error al crear el usuario");
        });
      }
      return response.json();
    })
    .then((data) => {
      alert("Usuario creado exitosamente");
      console.log("Respuesta del servidor:", data);
      document.getElementById("register-form").reset();
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Ocurrió un error: " + error.message);
    });
}
