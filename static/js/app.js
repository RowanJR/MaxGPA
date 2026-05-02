const API_BASE = '';

const MAJOR_LABELS = {
  cs_bs:       'BS Computer Science',
  bs_business: 'BS Business Administration',
  geog_bs:     'BS Physics',
};

let bestPathMode = false;
let lastData     = null;

function showState(name) {
  ['empty', 'loading', 'error'].forEach(s => {
    document.getElementById(`state-${s}`).classList.toggle('visible', s === name);
  });
}

function showReport(visible) {
  document.getElementById('report-meta').classList.toggle('visible', visible);
  document.getElementById('legend').classList.toggle('visible', visible);
  document.getElementById('best-path-controls').classList.toggle('visible', visible);
  if (!visible) {
    document.getElementById('best-path-panel').classList.remove('visible');
  }
}

async function fetchMajorData(major, yearFrom, yearTo) {
  const params = new URLSearchParams({ major, year_from: yearFrom, year_to: yearTo });
  const res = await fetch(`${API_BASE}/api/grades?${params}`);
  if (!res.ok) throw new Error(`Server responded with ${res.status}`);
  return res.json();
}

function renderBarGroup(gradeData) {
  const grades  = ['A', 'B', 'C', 'DNF'];
  const classes = ['grade-a', 'grade-b', 'grade-c', 'grade-dnf'];
  const MAX_H   = 60;

  if (!gradeData) {
    return `<div class="bar-group">${grades.map(g => `
      <div class="bar-col">
        <div class="bar-fill placeholder" style="height:${MAX_H / 2}px"></div>
        <span class="bar-tick">${g}</span>
      </div>`).join('')}
    </div>`;
  }

  const vals = grades.map(g => gradeData[g] ?? 0);
  const max = Math.max(...vals, 1);

  return `<div class="bar-group">${grades.map((g, i) => `
      <div class="bar-col">
        <div class="bar-fill ${classes[i]}" style="height:${Math.round((vals[i] / max) * MAX_H)}px"
             title="${g}: ${vals[i]}%"></div>
        <span class="bar-tick">${g}</span>
      </div>`).join('')}
    </div>`;
}

function renderCourseCard(course, delay, bestPath) {
  let instructors = course.instructors || [];

  if (bestPath) {
    const allInst = instructors.find(i => i.name === 'All Instructors');
    const best    = instructors.find(i => i.name !== 'All Instructors');
    instructors   = [allInst, best].filter(Boolean);
  }

  const instructorCols = instructors.map(inst => `
    <div class="chart-block${inst.name !== 'All Instructors' && bestPath ? ' best-pick' : ''}">
      <div class="chart-instructor" title="${inst.name}">${inst.name}</div>
      ${renderBarGroup(inst.grades)}
    </div>
  `).join('');

  return `
    <div class="course-card" style="animation-delay:${delay}ms">
      <div class="course-top">
        <span class="course-code">${course.code}</span>
        <span class="course-title">${course.title}</span>
        <span class="course-credits">${course.credits ?? ''} cr</span>
      </div>
      <div class="charts-row">${instructorCols || '<p style="font-size:13px;color:var(--ink-faint)">No instructor data available.</p>'}</div>
    </div>`;
}

function renderBestPathSummary(data) {
  const allCourses = data.terms.flatMap(t => t.courses);
  const rows = allCourses.map(course => {
    const best = (course.instructors || []).find(i => i.name !== 'All Instructors');
    const pctA = best ? best.grades.A : null;
    return `
      <tr>
        <td><span class="course-code">${course.code}</span></td>
        <td>${course.title}</td>
        <td>${best ? best.name : '—'}</td>
        <td class="pct-cell">${pctA !== null ? `<span class="pct-a">${pctA}%</span>` : '—'}</td>
      </tr>`;
  }).join('');

  document.getElementById('best-path-panel').innerHTML = `
    <h3 class="bp-heading">Recommended Instructor Per Course</h3>
    <p class="bp-sub">Instructor with the highest % A in the selected year range.</p>
    <table class="bp-table">
      <thead>
        <tr><th>Course</th><th>Title</th><th>Best Instructor</th><th>% A</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
  document.getElementById('best-path-panel').classList.add('visible');
}

function renderReport(data, bestPath) {
  const list = document.getElementById('course-list');
  list.innerHTML = '';

  let delay = 0;
  let currentYear = null;

  data.terms.forEach(term => {
    if (term.year !== currentYear) {
      currentYear = term.year;
      const h = document.createElement('div');
      h.className = 'year-heading';
      h.textContent = term.year;
      list.appendChild(h);
    }

    const t = document.createElement('div');
    t.className = 'term-heading';
    t.textContent = term.term;
    list.appendChild(t);

    term.courses.forEach(course => {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = renderCourseCard(course, delay, bestPath);
      list.appendChild(wrapper.firstElementChild);
      delay += 40;
    });
  });

  document.getElementById('report-title').textContent = data.major;
  document.getElementById('report-subtitle').textContent =
    `Grade data ${data.years} · Generated ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`;
}

function handleBestPath() {
  if (!lastData) return;
  bestPathMode = !bestPathMode;

  const btn = document.getElementById('btn-best-path');
  btn.classList.toggle('active', bestPathMode);
  btn.textContent = bestPathMode ? 'Best Path: ON' : 'Best Path';

  renderReport(lastData, bestPathMode);

  if (bestPathMode) {
    renderBestPathSummary(lastData);
  } else {
    document.getElementById('best-path-panel').classList.remove('visible');
  }
}

async function handleGenerate() {
  const major    = document.getElementById('major-select').value;
  const yearFrom = document.getElementById('year-from').value;
  const yearTo   = document.getElementById('year-to').value;

  if (!major) {
    alert('Please select a major first.');
    return;
  }

  bestPathMode = false;
  document.getElementById('btn-best-path').classList.remove('active');
  document.getElementById('btn-best-path').textContent = 'Best Path';
  document.getElementById('best-path-panel').classList.remove('visible');

  const btn = document.getElementById('btn-generate');
  btn.disabled = true;
  btn.textContent = 'Loading…';

  showReport(false);
  showState('loading');
  document.getElementById('course-list').innerHTML = '';

  try {
    const data = await fetchMajorData(major, yearFrom, yearTo);
    lastData = data;
    showState(null);
    showReport(true);
    renderReport(data, false);
  } catch (err) {
    showState('error');
    document.getElementById('error-message').textContent = err.message;
    showReport(false);
    console.error('MaxGPA fetch error:', err);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate report';
  }
}

document.getElementById('year-from').addEventListener('change', function () {
  const to = document.getElementById('year-to');
  if (parseInt(this.value) >= parseInt(to.value)) {
    to.value = String(parseInt(this.value) + 1);
  }
});

// ─── Year Dropdown Population ─────────────────────────────────────────────────

async function populateYears() {
  try {
    const res  = await fetch('/api/years');
    const data = await res.json();
    const years = data.years;  // sorted array of AY start ints, e.g. [2016, 2017, …]

    if (!years || years.length === 0) return;

    const fromSel = document.getElementById('year-from');
    const toSel   = document.getElementById('year-to');

    // Remember current selections (or fall back to sensible defaults)
    const prevFrom = parseInt(fromSel.value) || years[Math.max(0, years.length - 5)];
    const prevTo   = parseInt(toSel.value)   || years[years.length - 1];

    // Rebuild year-from: all years except the last (can't have a range of 0)
    fromSel.innerHTML = years.slice(0, -1).map(y =>
      `<option value="${y}"${y === prevFrom ? ' selected' : ''}>AY ${y}</option>`
    ).join('');

    // Rebuild year-to: all years except the first
    toSel.innerHTML = years.slice(1).map(y =>
      `<option value="${y}"${y === prevTo ? ' selected' : ''}>AY ${y}</option>`
    ).join('');

    // Ensure from < to after rebuild
    const fromVal = parseInt(fromSel.value);
    const toVal   = parseInt(toSel.value);
    if (fromVal >= toVal) {
      toSel.value = String(years[years.indexOf(fromVal) + 1] ?? years[years.length - 1]);
    }

  } catch (err) {
    console.error('Could not load year list:', err);
  }
}

// Populate on page load
populateYears();

// ─── Admin Panel ──────────────────────────────────────────────────────────────

let selectedFile = null;

function toggleAdmin() {
  const panel = document.getElementById('admin-panel');
  const btn   = document.getElementById('btn-admin-toggle');
  const open  = panel.classList.toggle('visible');
  btn.classList.toggle('active', open);
  if (!open) {
    clearFile();
    setUploadStatus('', '');
  }
}

function handleFileSelected(event) {
  const file = event.target.files[0];
  if (file) setFile(file);
}

function setFile(file) {
  selectedFile = file;
  document.getElementById('upload-filename').textContent = file.name;
  document.getElementById('upload-file-preview').style.display = 'flex';
  document.getElementById('upload-drop-zone').style.display = 'none';
  document.getElementById('btn-upload').disabled = false;
  setUploadStatus('', '');
}

function clearFile() {
  selectedFile = null;
  document.getElementById('csv-file-input').value = '';
  document.getElementById('upload-file-preview').style.display = 'none';
  document.getElementById('upload-drop-zone').style.display = 'block';
  document.getElementById('btn-upload').disabled = true;
  setUploadStatus('', '');
}

function setUploadStatus(message, type) {
  const el = document.getElementById('upload-status');
  el.textContent = message;
  el.className = `upload-status${type ? ' ' + type : ''}`;
}

function handleDragOver(event) {
  event.preventDefault();
  document.getElementById('upload-drop-zone').classList.add('drag-over');
}

function handleDragLeave(event) {
  document.getElementById('upload-drop-zone').classList.remove('drag-over');
}

function handleDrop(event) {
  event.preventDefault();
  document.getElementById('upload-drop-zone').classList.remove('drag-over');
  const file = event.dataTransfer.files[0];
  if (file && file.name.toLowerCase().endsWith('.csv')) {
    setFile(file);
  } else {
    setUploadStatus('Please drop a .csv file.', 'error');
  }
}

async function uploadCSV() {
  if (!selectedFile) return;

  const btn = document.getElementById('btn-upload');
  btn.disabled = true;
  btn.textContent = 'Uploading…';
  setUploadStatus('Uploading and importing data…', 'loading');

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const res = await fetch('/api/admin/upload-csv', {
      method: 'POST',
      body: formData,
    });

    const json = await res.json();

    if (!res.ok) {
      setUploadStatus(`Error: ${json.error || 'Upload failed.'}`, 'error');
    } else {
      setUploadStatus(
        `✓ Imported ${json.rows_imported} rows from "${json.filename}". Duplicates removed: ${json.duplicates_removed}.`,
        'success'
      );
      clearFile();
      populateYears();  // Refresh dropdowns in case new years were added
    }
  } catch (err) {
    setUploadStatus(`Network error: ${err.message}`, 'error');
    console.error('Admin upload error:', err);
  } finally {
    btn.disabled = !selectedFile;
    btn.textContent = 'Upload CSV';
  }
}