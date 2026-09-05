chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
  if (request.action === "urlSentSuccess") {
    // Sayfadaki çalan videoları bulup durdur (Gönderildiğini belli etmek için)
    const videos = document.querySelectorAll('video');
    videos.forEach(video => {
      if (!video.paused) {
        video.pause();
      }
    });
    console.log("uDesk: Link başarıyla gönderildi.");
  }
});