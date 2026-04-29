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

function renderSkeletons(count = 4) {
  const area = document.getElementById('skeleton-area');
  area.innerHTML = Array.from({ length: count }, () => `
    <div class="skeleton-card">
      <div class="skel skel-title"></div>
      <div class="skel skel-bars"></div>
    </div>
  `).join('');
  document.getElementById('state-loading').classList.add('visible');
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
      ${renderBarGroup(inst.grades)}
      <div class="chart-instructor" title="${inst.name}">${inst.name}</div>
      ${inst.name !== 'All Instructors' && bestPath ? '<div class="best-badge">Best</div>' : ''}
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
  renderSkeletons(5);
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
