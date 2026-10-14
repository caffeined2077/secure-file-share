//
// LOGIN
//

const loginForm = document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener("submit", async function(event) {

        event.preventDefault();

        const username =
            document.getElementById("username").value;

        const password =
            document.getElementById("password").value;

        const message =
            document.getElementById("message");


        const response = await fetch("/login", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                username: username,
                password: password
            })

        });


        const data = await response.json();


        if (data.access_token) {

            // Save JWT token
            localStorage.setItem(
                "token",
                data.access_token
            );

            // Save username
            localStorage.setItem(
                "username",
                data.username
            );

            message.textContent =
                "Login successful!";

            window.location.href =
                "/dashboard";

        } else {

            message.textContent =
                data.message;

        }

    });

}


//
// REGISTER
//

const registerForm =
    document.getElementById("registerForm");

if (registerForm) {

    registerForm.addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();

            const username =
                document.getElementById("username").value;

            const email =
                document.getElementById("email").value;

            const password =
                document.getElementById("password").value;


            const response = await fetch(
                "/register",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        username: username,
                        email: email,
                        password: password
                    })

                }
            );


            const data =
                await response.json();


            document.getElementById(
                "message"
            ).textContent = data.message;


            if (data.username) {

                setTimeout(function() {

                    window.location.href = "/";

                }, 1000);

            }

        }
    );

}


//
// DASHBOARD
//

const uploadForm =
    document.getElementById("uploadForm");

if (uploadForm) {

    // Show username

    document.getElementById(
        "username"
    ).textContent =
        localStorage.getItem("username");


    //
    // LOGOUT
    //

    document.getElementById(
        "logoutButton"
    ).addEventListener("click", function() {

        localStorage.removeItem("token");
        localStorage.removeItem("username");

        window.location.href = "/";

    });


    //
    // UPLOAD FILE
    //

    uploadForm.addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            const file =
                document.getElementById(
                    "fileInput"
                ).files[0];


            const token =
                localStorage.getItem("token");


            const formData =
                new FormData();

            formData.append(
                "uploaded_file",
                file
            );


            const response = await fetch(
                "/upload",
                {

                    method: "POST",

                    headers: {
                        "Authorization":
                            "Bearer " + token
                    },

                    body: formData

                }
            );


            const data =
                await response.json();


            if (data.code) {

                document.getElementById(
                    "uploadMessage"
                ).textContent =
                    "File uploaded successfully!";


                document.getElementById(
                    "uploadedFilename"
                ).textContent =
                    data.filename;


                document.getElementById(
                    "fileCode"
                ).textContent =
                    data.code;


                document.getElementById(
                    "expiresAt"
                ).textContent =
                    new Date(
                        data.expires_at
                    ).toLocaleString();


                document.getElementById(
                    "uploadResult"
                ).style.display =
                    "block";

            } else {

                document.getElementById(
                    "uploadMessage"
                ).textContent =
                    data.message;

            }

        }
    );


    //
    // DOWNLOAD FILE
    //

    const downloadForm =
        document.getElementById(
            "downloadForm"
        );


    downloadForm.addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            const code =
                document.getElementById(
                    "downloadCode"
                ).value;


            const response =
                await fetch(
                    "/download-by-code",
                    {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            code: code
                        })

                    }
                );


            // If server sends an error

            if (
                response.headers
                .get("content-type")
                .includes("application/json")
            ) {

                const data =
                    await response.json();

                document.getElementById(
                    "downloadMessage"
                ).textContent =
                    data.message;

                return;
            }


            // Get the file

            const blob =
                await response.blob();


            // Create download link

            const link =
                document.createElement("a");

            link.href =
                window.URL.createObjectURL(blob);

            link.download =
                "downloaded_file";

            link.click();


            document.getElementById(
                "downloadMessage"
            ).textContent =
                "File downloaded successfully!";

        }
    );

}