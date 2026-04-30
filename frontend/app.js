/*
File: app.js

Purpose:
Handles frontend behavior for the MaxGPA web application. This includes
fetching data from the backend API, updating UI states, and rendering
course and instructor grade visualizations.

System Context:
This file is part of the MaxGPA system. It serves as the client-side logic
that communicates with the Flask backend (app.py) and dynamically updates
the webpage based on user input and API responses.

Authors:
- Jacob Seiberg

Date Created:
04/16/2026

Modifications:
- 04/23/2026: Implemented frontend rendering logic for course data.
- 04/29/2026: Integrated API calls to backend and improved UI updates.
- 04/30/2026: Added improved loading states and animations.
*/


// ---------------------------------------------------------------------
// Configuration Variables
// ---------------------------------------------------------------------

const API_BASE = '';
// Base URL for API requests (empty string means same host)

const MAJOR_LABELS = {
  cs_bs:       'BS Computer Science',
  bs_business: 'BS Business Administration',
  geog_bs:     'BS Geography',
};
// Maps backend major keys to display labels for UI


// ---------------------------------------------------------------------
// UI State Management
// ---------------------------------------------------------------------

function showState(name) {
  // Toggle visibility of UI states (empty, loading, error)
  ['empty', 'loading', 'error'].forEach(s => {
    document.getElementById(`state-${s}`).classList.toggle('visible', s === name);
  });
}

function showReport(visible) {
  // Show or hide the report section
  document.getElementById('report-meta').classList.toggle('visible', visible);
  document.getElementById('legend').classList.toggle('visible', visible);
}


// ---------------------------------------------------------------------
// Loading Skeleton UI
// ---------------------------------------------------------------------

function renderSkeletons(count = 4) {
  // Display placeholder cards while data is loading
  const area = document.getElementById('skeleton-area');

  area.innerHTML = Array.from({ length: count }, () => `
    <div class="skeleton-card">
      <div class="skel skel-title"></div>
      <div class="skel skel-bars"></div>
    </div>
  `).join('');

  document.getElementById('state-loading').classList.add('visible');
}


// ---------------------------------------------------------------------
// API Communication
// ---------------------------------------------------------------------

async function fetchMajorData(major, yearFrom, yearTo) {
  // Build query parameters for API request
  const params = new URLSearchParams({ major, year_from: yearFrom, year_to: yearTo });

  // Send GET request to backend API
  const res = await fetch(`${API_BASE}/api/grades?${params}`);

  // Throw error if request fails
  if (!res.ok) throw new Error(`Server responded with ${res.status}`);

  // Return parsed JSON response
  return res.json();
}


// ---------------------------------------------------------------------
// Chart Rendering
// ---------------------------------------------------------------------

function renderBarGroup(gradeData) {
  // Define grade categories and styling classes
  const grades  = ['A', 'B', 'C', 'DNF'];
  const classes = ['grade-a', 'grade-b', 'grade-c', 'grade-dnf'];
  const MAX_H   = 60; // Maximum bar height

  // If no data is available, render placeholder bars
  if (!gradeData) {
    return `<div class="bar-group">${grades.map(g => `
      <div class="bar-col">
        <div class="bar-fill placeholder" style="height:${MAX_H / 2}px"></div>
        <span class="bar-tick">${g}</span>
      </div>`).join('')}
    </div>`;
  }

  // Extract values for each grade
  const vals = grades.map(g => gradeData[g] ?? 0);

  // Determine scaling factor for bar heights
  const max = Math.max(...vals, 1);

  // Generate HTML for bar chart
  return `<div class="bar-group">${grades.map((g, i) => `
      <div class="bar-col">
        <div class="bar-fill ${classes[i]}" style="height:${Math.round((vals[i] / max) * MAX_H)}px"
             title="${g}: ${vals[i]}%"></div>
        <span class="bar-tick">${g}</span>
      </div>`).join('')}
    </div>`;
}


// ---------------------------------------------------------------------
// Course Card Rendering
// ---------------------------------------------------------------------

function renderCourseCard(course, delay) {
  // Render instructor chart blocks for a course
  const instructorCols = (course.instructors || []).map(inst => `
    <div class="chart-block">
      ${renderBarGroup(inst.grades)}
      <div class="chart-instructor" title="${inst.name}">${inst.name}</div>
    </div>
  `).join('');

  // Return HTML for course card
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


// ---------------------------------------------------------------------
// Report Rendering
// ---------------------------------------------------------------------

function renderReport(data) {
  const list = document.getElementById('course-list');
  list.innerHTML = '';

  let delay = 0;
  let currentYear = null;

  // Loop through each term and render its courses
  data.terms.forEach(term => {

    // Add year heading when year changes
    if (term.year !== currentYear) {
      currentYear = term.year;
      const h = document.createElement('div');
      h.className = 'year-heading';
      h.textContent = term.year;
      list.appendChild(h);
    }

    // Add term heading
    const t = document.createElement('div');
    t.className = 'term-heading';
    t.textContent = term.term;
    list.appendChild(t);

    // Render each course
    term.courses.forEach(course => {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = renderCourseCard(course, delay);
      list.appendChild(wrapper.firstElementChild);
      delay += 40;
    });
  });

  // Update report title and subtitle
  document.getElementById('report-title').textContent = data.major;
  document.getElementById('report-subtitle').textContent =
    `Grade data ${data.years} · Generated ${new Date().toLocaleDateString('en-US')}`;
}


// ---------------------------------------------------------------------
// Main Button Handler
// ---------------------------------------------------------------------

async function handleGenerate() {

  // Get user-selected inputs
  const major    = document.getElementById('major-select').value;
  const yearFrom = document.getElementById('year-from').value;
  const yearTo   = document.getElementById('year-to').value;

  // Prevent execution if no major selected
  if (!major) {
    alert('Please select a major first.');
    return;
  }

  const btn = document.getElementById('btn-generate');

  // Disable button and show loading state
  btn.disabled = true;
  btn.textContent = 'Loading…';

  showReport(false);
  showState('loading');
  renderSkeletons(5);
  document.getElementById('course-list').innerHTML = '';

  try {
    // Fetch data from backend
    const data = await fetchMajorData(major, yearFrom, yearTo);

    // Render successful results
    showState(null);
    showReport(true);
    renderReport(data);

  } catch (err) {
    // Handle errors
    showState('error');
    document.getElementById('error-message').textContent = err.message;
    showReport(false);
    console.error('MaxGPA fetch error:', err);

  } finally {
    // Re-enable button after request completes
    btn.disabled = false;
    btn.textContent = 'Generate report';
  }
}


// ---------------------------------------------------------------------
// Input Validation
// ---------------------------------------------------------------------

document.getElementById('year-from').addEventListener('change', function () {

  // Ensure "year to" is always greater than "year from"
  const to = document.getElementById('year-to');

  if (parseInt(this.value) >= parseInt(to.value)) {
    to.value = String(parseInt(this.value) + 1);
  }
});