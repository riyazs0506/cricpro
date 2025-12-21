var socket = io();

socket.emit("join", { room: ROOM });

socket.on("receive_message", function(data){
    let box = document.getElementById("chatBox");
    box.innerHTML += `
        <div class="msg sent">
            ${data.message}
            <span class="tick">✔</span>
        </div>
    `;
});
