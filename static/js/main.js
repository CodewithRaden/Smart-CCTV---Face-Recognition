document.addEventListener('DOMContentLoaded', function () {
    const startRecordButton = document.getElementById('startRecord');
    const stopRecordButton = document.getElementById('stopRecord');
    const videoPlayer = document.getElementById('videoPlayer');

    let mediaRecorder;
    let recordedChunks = [];

    startRecordButton.addEventListener('click', startRecording);
    stopRecordButton.addEventListener('click', stopRecording);

    async function startRecording() {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: 'video/webm' });
            const url = URL.createObjectURL(blob);
            videoPlayer.src = url;
        };

        mediaRecorder.start();
        startRecordButton.disabled = true;
        stopRecordButton.disabled = false;
    }

    function stopRecording() {
        mediaRecorder.stop();
        startRecordButton.disabled = false;
        stopRecordButton.disabled = true;
    }
});
