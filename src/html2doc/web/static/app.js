const form = document.getElementById('upload-form');
const fileInput = document.getElementById('archive');
const panel = document.getElementById('status-panel');
const statusText = document.getElementById('status-text');
const progress = document.getElementById('progress');
const progressLabel = document.getElementById('progress-label');
const logElement = document.getElementById('log');
const download = document.getElementById('download');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = new FormData();
  data.append('file', fileInput.files[0]);

  panel.hidden = false;
  download.hidden = true;
  logElement.textContent = '';
  statusText.textContent = 'Загрузка архива…';

  try {
    const response = await fetch('/api/jobs', { method: 'POST', body: data });
    if (!response.ok) {
      const detail = await response.json();
      throw new Error(detail.detail || 'Ошибка загрузки');
    }
    const job = await response.json();
    await poll(job.job_id);
  } catch (error) {
    statusText.textContent = 'Ошибка';
    logElement.textContent = error.message;
  }
});

async function poll(jobId) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
  const job = await response.json();

  statusText.textContent = job.message;
  progress.max = Math.max(job.total || 1, 1);
  progress.value = job.current || 0;
  progressLabel.textContent = `${job.current || 0} / ${job.total || 0}`;
  logElement.textContent = job.logs.map((item) => `[${item.level}] ${item.message}`).join('\n');

  if (job.status === 'done') {
    download.href = `/api/jobs/${encodeURIComponent(jobId)}/result`;
    download.hidden = false;
    return;
  }
  if (job.status === 'error') {
    statusText.textContent = 'Ошибка обработки';
    logElement.textContent += `\n${job.error || ''}`;
    return;
  }
  setTimeout(() => poll(jobId), 700);
}
