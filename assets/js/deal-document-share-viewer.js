import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@5.6.205/build/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdn.jsdelivr.net/npm/pdfjs-dist@5.6.205/build/pdf.worker.min.mjs";

const viewerRoot = document.getElementById("share-pdf-viewer");
const pagesContainer = document.getElementById("share-pdf-viewer-pages");
const statusNode = document.getElementById("share-pdf-viewer-status");

if (!viewerRoot || !pagesContainer || !statusNode) {
  throw new Error("PDF viewer root not found.");
}

const previewUrl = viewerRoot.dataset.previewUrl || "";
const eventUrl = viewerRoot.dataset.eventUrl || "";

let pdfDocument = null;
let currentPageNumber = 1;
let lastObservedPage = 1;
let viewerClosedSent = false;
let lastPageReachedSent = false;
let documentOpenedSent = false;
let accumulatedVisibleMs = 0;
let visibleStartedAt = document.visibilityState === "visible" ? performance.now() : null;
const viewedPages = new Set();

function setStatus(text) {
  statusNode.textContent = text;
}

function roundedSeconds(durationMs) {
  return Math.max(0, Math.round(durationMs / 1000));
}

function currentVisibleDurationMs() {
  if (visibleStartedAt === null) {
    return accumulatedVisibleMs;
  }
  return accumulatedVisibleMs + (performance.now() - visibleStartedAt);
}

function markHidden() {
  if (visibleStartedAt !== null) {
    accumulatedVisibleMs += performance.now() - visibleStartedAt;
    visibleStartedAt = null;
  }
}

function markVisible() {
  if (visibleStartedAt === null) {
    visibleStartedAt = performance.now();
  }
}

async function postEvent(eventType, metadata = {}, useBeacon = false) {
  if (!eventUrl) {
    return;
  }
  const payload = JSON.stringify({
    event_type: eventType,
    metadata,
  });
  if (useBeacon && navigator.sendBeacon) {
    const blob = new Blob([payload], { type: "application/json" });
    navigator.sendBeacon(eventUrl, blob);
    return;
  }
  try {
    await fetch(eventUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: payload,
      credentials: "same-origin",
      keepalive: useBeacon,
    });
  } catch (_error) {
    // Public viewer analytics should not break document rendering.
  }
}

function flushCloseEvents() {
  if (viewerClosedSent || !documentOpenedSent) {
    return;
  }
  viewerClosedSent = true;
  markHidden();
  const durationMs = Math.round(currentVisibleDurationMs());
  const durationSeconds = roundedSeconds(durationMs);
  const commonMetadata = {
    current_page: currentPageNumber,
    last_observed_page: lastObservedPage,
    total_pages: pdfDocument ? pdfDocument.numPages : null,
  };
  postEvent("viewer_closed", commonMetadata, true);
  postEvent(
    "time_in_viewer",
    {
      ...commonMetadata,
      duration_ms: durationMs,
      duration_seconds: durationSeconds,
    },
    true,
  );
}

function updateCurrentPage(pageNumber) {
  currentPageNumber = pageNumber;
  lastObservedPage = Math.max(lastObservedPage, pageNumber);
  const totalPages = pdfDocument ? pdfDocument.numPages : "?";
  setStatus(`Страница ${pageNumber} из ${totalPages}`);
}

function trackPageVisibility(pageNode, pageNumber, totalPages) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.6) {
          continue;
        }
        updateCurrentPage(pageNumber);
        if (!viewedPages.has(pageNumber)) {
          viewedPages.add(pageNumber);
          postEvent("page_viewed", {
            page_number: pageNumber,
            total_pages: totalPages,
          });
        }
        if (pageNumber === totalPages && !lastPageReachedSent) {
          lastPageReachedSent = true;
          postEvent("last_page_reached", {
            page_number: pageNumber,
            total_pages: totalPages,
          });
        }
      }
    },
    {
      root: pagesContainer,
      threshold: [0.6],
    },
  );
  observer.observe(pageNode);
}

async function renderPage(pageNumber, totalPages) {
  const page = await pdfDocument.getPage(pageNumber);
  const pageNode = document.createElement("section");
  pageNode.className = "viewer-page";
  pageNode.dataset.pageNumber = String(pageNumber);

  const canvas = document.createElement("canvas");
  const caption = document.createElement("div");
  caption.className = "viewer-page-meta";
  caption.textContent = `Страница ${pageNumber}`;

  pageNode.appendChild(canvas);
  pageNode.appendChild(caption);
  pagesContainer.appendChild(pageNode);

  const unscaledViewport = page.getViewport({ scale: 1 });
  const containerWidth = Math.max(320, pagesContainer.clientWidth - 60);
  const scale = Math.min(1.7, Math.max(0.75, containerWidth / unscaledViewport.width));
  const viewport = page.getViewport({ scale });
  const outputScale = window.devicePixelRatio || 1;
  const context = canvas.getContext("2d");

  canvas.width = Math.floor(viewport.width * outputScale);
  canvas.height = Math.floor(viewport.height * outputScale);
  canvas.style.width = `${Math.floor(viewport.width)}px`;
  canvas.style.height = `${Math.floor(viewport.height)}px`;

  const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : null;
  await page.render({
    canvasContext: context,
    viewport,
    transform,
  }).promise;

  trackPageVisibility(pageNode, pageNumber, totalPages);
}

async function renderDocument() {
  pagesContainer.innerHTML = '<div class="viewer-empty">Загружаем PDF…</div>';
  const loadingTask = pdfjsLib.getDocument({
    url: previewUrl,
    withCredentials: true,
  });
  pdfDocument = await loadingTask.promise;

  if (!documentOpenedSent) {
    documentOpenedSent = true;
    postEvent("document_opened", { total_pages: pdfDocument.numPages });
  }

  pagesContainer.innerHTML = "";
  setStatus(`Страница 1 из ${pdfDocument.numPages}`);

  for (let pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber += 1) {
    await renderPage(pageNumber, pdfDocument.numPages);
  }
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    markHidden();
    return;
  }
  markVisible();
});

window.addEventListener("pagehide", flushCloseEvents);
window.addEventListener("beforeunload", flushCloseEvents);

renderDocument().catch((error) => {
  console.error(error);
  setStatus("Не удалось загрузить PDF");
  pagesContainer.innerHTML = '<div class="viewer-empty">Viewer не смог отрисовать PDF. Откройте исходный PDF или скачайте файл.</div>';
});
