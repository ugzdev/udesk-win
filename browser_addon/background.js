// --- BÖLÜM 1: Eklenti İkonuna Tıklayınca Çalışan Kısım ---
chrome.action.onClicked.addListener((tab) => {
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      let currentUrl = window.location.href;
      let videoElement = document.querySelector('video');
      let currentTime = 0;

      if (videoElement) {
        currentTime = Math.floor(videoElement.currentTime);
        // VİDEOYU BURADA DOĞRUDAN DURDURUYORUZ
        if (!videoElement.paused) {
          videoElement.pause();
        }
      }

      if (currentUrl.includes("youtube.com/watch")) {
        let urlObj = new URL(currentUrl);
        urlObj.searchParams.set("t", currentTime + "s");
        return urlObj.toString();
      }
      return currentUrl;
    }
  }, (results) => {
    let finalUrl = tab.url;
    if (results && results[0].result) {
      finalUrl = results[0].result;
    }

    fetch("http://localhost:51481/send_url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: finalUrl, page_url: tab.url })
    }).then(res => {
      console.log("Sayfa URL Gönderildi!");
    }).catch(err => console.error("Hata:", err));
  });
});

// --- BÖLÜM 2: Sağ Tık Menüsü Ekleme ve Yönetimi (uDesk & MiniWeb) ---
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "sendPageToUdeskContextMenu",
    title: "uDesk Browser",
    contexts: ["all"]
  });

  chrome.contextMenus.create({
    id: "sendToMiniWebContextMenu",
    title: "uDesk MiniWeb",
    contexts: ["all"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  // SEÇENEK 1: uDesk'e Gönder
  if (info.menuItemId === "sendPageToUdeskContextMenu" && tab) {
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        let currentUrl = window.location.href;
        let videoElement = document.querySelector('video');
        let currentTime = 0;

        if (videoElement) {
          currentTime = Math.floor(videoElement.currentTime);
          // VİDEOYU BURADA DOĞRUDAN DURDURUYORUZ
          if (!videoElement.paused) {
            videoElement.pause();
          }
        }

        if (currentUrl.includes("youtube.com/watch")) {
          let urlObj = new URL(currentUrl);
          urlObj.searchParams.set("t", currentTime + "s");
          return urlObj.toString();
        }
        return currentUrl;
      }
    }, (results) => {
      let finalUrl = tab.url;
      if (results && results[0].result) {
        finalUrl = results[0].result;
      }

      fetch("http://localhost:51481/send_url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: finalUrl, page_url: tab.url })
      }).then(res => {
        console.log("Sağ tık ile uDesk'e URL Gönderildi!");
      }).catch(err => console.error("Sağ tık uDesk gönderim hatası:", err));
    });
  }

  // SEÇENEK 2: MiniWeb'e Gönder
  else if (info.menuItemId === "sendToMiniWebContextMenu" && tab) {
    // Miniweb'e gönderirken de videoyu durdurması için ufak bir script enjekte ediyoruz
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        let videos = document.querySelectorAll('video');
        videos.forEach(v => v.pause());
      }
    });

    fetch("http://localhost:51481/send_url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mini_url: tab.url
      })
    }).then(res => {
      console.log("Sağ tık ile Mini Web'e Sadece URL Gönderildi!");
    }).catch(err => console.error("MiniWeb gönderim hatası:", err));
  }
});