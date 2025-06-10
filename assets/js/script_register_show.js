function createUser() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("new-password").value;
  const confirmPassword = document.getElementById("confirm-password").value;

  // Validación de campos vacíos
  if (!username || !password || !confirmPassword) {
    alert("Por favor, completa todos los campos.");
    return;
  }

  // Validación de coincidencia de contraseñas
  if (password !== confirmPassword) {
    alert("Las contraseñas no coinciden.");
    return;
  }

  // Crear el objeto de usuario
  const user = {
    username: username,
    hashed_password: password,
  };

  // Enviar al backend
  fetch("https://login-fastapi-9b3b.onrender.com/users/me/create", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
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
      // Limpiar formulario si deseas
      document.getElementById("register-form").reset();
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Ocurrió un error: " + error.message);
    });
}
