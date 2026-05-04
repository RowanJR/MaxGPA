// -------------------------------------------------------------------------------------
// File:    app.js
// Purpose: This file contains the client side logic for MaxGPA. It handles
//          selecting majors and years, fetching data from the API, rendering
//          course cards, and the Best Path functionality. This file also manages
//          admin mode and new grade data upload.
//
// Created: 2025
// Author: Jake Seiberg
//
// Modifications:
//   2025-04-23 Jake Seiberg — Basic functionality
//   2025-04-27 Jake Seiberg — Connected to the backend API
//   2025-04-30 Jake Seiberg — Data display
//   2025-05-01 Jake Seiberg — Implemented Best Path mode
//   2025-05-02 Jake Seiberg — Implemented Admin Panel
//   2025-05-03 Jake Seiberg — Bug fixes
//
// -------------------------------------------------------------------------------------

const API_BASE = ''; // Base URL for the API (empty for local development)

let bestPathMode = false; //Current state of the Best Path mode
let lastData     = null; // Last fetched data


// -----UI State Management---------------------------------------

function showState(name) {
  //Show one of the three UI states
  ['empty', 'loading', 'error'].forEach(s => {
    document.getElementById(`state-${s}`).classList.toggle('visible', s === name);
  });
}

function showReport(visible) {
  //Shows or hides the report, legend, and best path button
  //Collapses the best path panel it is open
  document.getElementById('report-meta').classList.toggle('visible', visible);
  document.getElementById('legend').classList.toggle('visible', visible);
  document.getElementById('best-path-controls').classList.toggle('visible', visible);
  if (!visible) {
    document.getElementById('best-path-panel').classList.remove('visible');
  }
}

//--------API Requests------------------------------------------

async function fetchMajorData(major, yearFrom, yearTo) {
  //Fetches grade data for the given major and years from the API
  //Returns the fetches JSON object, or throws an error on a failed request
  const params = new URLSearchParams({ major, year_from: yearFrom, year_to: yearTo }); //URL parameters
  const res = await fetch(`${API_BASE}/api/grades?${params}`);
  
  if (!res.ok) throw new Error(`Server responded with ${res.status}`);

  return res.json();
}


//--------Chart Rendering----------------------------------------

function renderBarGroup(gradeData) {
  //Constructs the HTML for a group of bars representing the grade
  //distribution for a single course.
  const grades  = ['A', 'B', 'C', 'DNF']; //Grade labels
  const classes = ['grade-a', 'grade-b', 'grade-c', 'grade-dnf']; //Corresponding CSS classes
  const MAX_H   = 60; //Max height of the bars

  //If no grade data was found, display a placeholder
  if (!gradeData) {
    return `<div class="bar-group">${grades.map(g => `
      <div class="bar-col">
        <div class="bar-fill placeholder" style="height:${MAX_H / 2}px"></div>
        <span class="bar-tick">${g}</span>
      </div>`).join('')}
    </div>`;
  }

  const vals = grades.map(g => gradeData[g] ?? 0);//finds the value for each grade, defaults to 0 if not found
  const max = Math.max(...vals, 1); //Scales the size of the bars for the largest value reachest the max height, minimum 1 to avoid division by zero

  //Creates the HTML for the bar group
  return `<div class="bar-group">${grades.map((g, i) => `
      <div class="bar-col">
        <div class="bar-fill ${classes[i]}" style="height:${Math.round((vals[i] / max) * MAX_H)}px"
             title="${g}: ${vals[i]}%"></div>
        <span class="bar-tick">${g}</span>
      </div>`).join('')}
    </div>`;
}

//--------Course Card Rendering---------------------------------

function renderCourseCard(course, bestPath) {
  //Builds the HTML for a course card, includes the course header and the
  //grade distribution for each instructor.
  // course - course object returned from the API
  // bestPath - boolean indicating if best path mode is active

  let instructors = course.instructors || [];

  //Only show the aggregate grade data and the best proffesor if in best path mode
  if (bestPath) {
    const allInst = instructors.find(i => i.name === 'All Instructors');
    const best    = instructors.find(i => i.name !== 'All Instructors');
    instructors   = [allInst, best].filter(Boolean);
  }

  //Builds the HTML for each instructor's grade distribution
  const instructorCols = instructors.map(inst => `
    <div class="chart-block${inst.name !== 'All Instructors' && bestPath ? ' best-pick' : ''}">
      <div class="chart-instructor" title="${inst.name}">${inst.name}</div>
      ${renderBarGroup(inst.grades)}
    </div>
  `).join('');

  return `
    <div class="course-card">
      <div class="course-top">
        <span class="course-code">${course.code}</span>
        <span class="course-title">${course.title}</span>
        <span class="course-credits">${course.credits ?? ''} cr</span>
      </div>
      <div class="charts-row">${instructorCols || '<p>No instructor data available.</p>'}</div>
    </div>`;
}

///--------Best Path Summary Rendering---------------------------

function renderBestPathSummary(data) {
  //Builds the HTML for the best path summary, displays the recommended instructors for each course
  
  const allCourses = data.terms.flatMap(t => t.courses); //Condenses courses into an array

  //Creates one row in the table for each course
  const rows = allCourses.map(course => {
    //Finds the best insturctor for each course
    const best = (course.instructors || []).find(i => i.name !== 'All Instructors');
    //Finds the instructors A percentage
    const pctA = best ? best.grades.A : null;

    return `
      <tr>
        <td><span class="course-code">${course.code}</span></td>
        <td>${course.title}</td>
        <td>${best ? best.name : '—'}</td>
        <td class="pct-cell">${pctA !== null ? `<span class="pct-a">${pctA}%</span>` : '—'}</td>
      </tr>`;
  }).join('');

  //Sends the HTML for the table to the best path panel
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

///--------Report Rendering-------------------------------------

function renderReport(data, bestPath) {
  //Rebuilds the course list and all terms and courses from the given data.
  //Headings get inserted before each term and course.
  const list = document.getElementById('course-list');
  list.innerHTML = ''; //Clears previously rendered HTML

  let curYear = null; //Tracks the current year

  data.terms.forEach(term => {
    //Insert a heading only when the year changes
    if (term.year !== curYear) {
      curYear = term.year;

      const h = document.createElement('div');

      h.className = 'year-heading';
      h.textContent = term.year;
      list.appendChild(h);
    }

    //Insert a heading for each term below the year heading
    const t = document.createElement('div');

    t.className = 'term-heading';
    t.textContent = term.term;
    list.appendChild(t);

    //Renders the course card and appends it to the list
    term.courses.forEach(course => {
      const wrapper = document.createElement('div');

      wrapper.innerHTML = renderCourseCard(course, bestPath);
      list.appendChild(wrapper.firstElementChild);
    });
  });

  //Updates the report title and subtitle with the data returned from the API
  document.getElementById('report-title').textContent = data.major;
  document.getElementById('report-subtitle').textContent =
    `Grade data ${data.years}`;
}

//-----------Event Handlers-------------------------------

function handleBestPath() {
  //Toggles the best path mode
  if (!lastData) {
    return; //No data to work with
  }

  bestPathMode = !bestPathMode;

  //update the lable on the best path button
  const btn = document.getElementById('btn-best-path');
  btn.classList.toggle('active', bestPathMode);
  btn.textContent = bestPathMode ? 'Best Path: ON' : 'Best Path';

  //renders based on the current best path mode
  renderReport(lastData, bestPathMode);

  //if in best path mode render the summary, else dont render the summary
  if (bestPathMode) {
    renderBestPathSummary(lastData);
  } else {
    document.getElementById('best-path-panel').classList.remove('visible');
  }
}

async function handleGenerate() {
  //Runs when the user generates a new report.
  //First validates the input then fetches the data from the API.
  //The button is disabled during the loading process until a report is rendered.
  const major = document.getElementById('major-select').value;
  const yearFrom = document.getElementById('year-from').value;
  const yearTo = document.getElementById('year-to').value;

  //You must selected a major
  if (!major) {
    alert('Please select a major first.');
    return;
  }

  //Resets best path mode to always start in the default view
  bestPathMode = false;
  document.getElementById('btn-best-path').classList.remove('active');
  document.getElementById('btn-best-path').textContent = 'Best Path';
  document.getElementById('best-path-panel').classList.remove('visible');

  //Disables the button and shows a loading message
  const btn = document.getElementById('btn-generate');
  btn.disabled = true;
  btn.textContent = 'Loading…';

  showReport(false);
  showState('loading');
  document.getElementById('course-list').innerHTML = '';

  try {
    //Fetch data from the API, a report is rendered on a success
    const data = await fetchMajorData(major, yearFrom, yearTo);
    lastData = data;
    showState(null);
    showReport(true);
    renderReport(data, false);
  } catch (err) {
    //Handles errors in the API call and reports the error message
    showState('error');
    document.getElementById('error-message').textContent = err.message;
    showReport(false);
    console.error('MaxGPA fetch error:', err);
  } finally {
    //re eanble the button regardless of result
    btn.disabled = false;
    btn.textContent = 'Generate report';
  }
}

//Prevents the second year from being less than the first year
document.getElementById('year-from').addEventListener('change', function () {
  const to = document.getElementById('year-to');
  if (parseInt(this.value) >= parseInt(to.value)) {
    to.value = String(parseInt(this.value) + 1);
  }
});

//------ Year dropdown population -----------------------------

async function populateYears() {
  try {
    // Creates a sorted array of academic years
    const res = await fetch('/api/years');
    const data = await res.json();
    const years = data.years;

    if (!years || years.length === 0) return;

    const fromSelection = document.getElementById('year-from');
    const toSelection   = document.getElementById('year-to');

    //Remembers the currently selecte years, defaults back to a set value if none are selected
    const prevFrom = parseInt(fromSelection.value) || years[Math.max(0, years.length - 5)];
    const prevTo = parseInt(toSelection.value) || years[years.length - 1];

    //prevents the first year from including the last year
    fromSelection.innerHTML = years.slice(0, -1).map(y =>
      `<option value="${y}"${y === prevFrom ? ' selected' : ''}>AY ${y}</option>`
    ).join('');

    //prevents the second year from including the first year
    toSelection.innerHTML = years.slice(1).map(y =>
      `<option value="${y}"${y === prevTo ? ' selected' : ''}>AY ${y}</option>`
    ).join('');

    //Ensures that the first year is still less than the second year
    const fromVal = parseInt(fromSelection.value);
    const toVal   = parseInt(toSelection.value);

    if (fromVal >= toVal) {
      toSelection.value = String(years[years.indexOf(fromVal) + 1] ?? years[years.length - 1]);
    }

  } catch (err) {
    //Logs error
    console.error('Could not load year list:', err);
  }
}

//Populate years when the page loads
populateYears();

//-------------Admin Panel--------------------------------------

let curFile = null; //The file the user has selected to upload

function toggleAdmin() {
  //Toggles the admin panel and resets the admin panel when it is closed
  const panel = document.getElementById('admin-panel');
  const btn = document.getElementById('btn-admin-toggle');
  const open = panel.classList.toggle('visible');
  
  btn.classList.toggle('active', open);
  //ends any current file upload when the admin panel is closed
  if (!open) {
    clearFile();
  }
}

function handleFileSelected(event) {
  //Finds the chosen file and gives it to setFile
  const file = event.target.files[0];
  if (file) setFile(file);
}

function setFile(file) {
  //Store the file as a pending upload, shows the file name, enables the upload button,
  // hides the drop zone, and sets the upload status to empty.
  curFile = file;

  document.getElementById('upload-filename').textContent = file.name;
  document.getElementById('upload-file-preview').style.display = 'flex';
  document.getElementById('upload-drop-zone').style.display = 'none';
  document.getElementById('btn-upload').disabled = false;

  setUploadStatus('', '');
}

function clearFile() {
  //Resets file selection by clearing the current file, resetting the input,
  // hides the file previews, and resets the upload status.
  curFile = null;

  document.getElementById('csv-file-input').value = '';
  document.getElementById('upload-file-preview').style.display = 'none';
  document.getElementById('upload-drop-zone').style.display = 'block';
  document.getElementById('btn-upload').disabled = true;
  
  setUploadStatus('', '');
}

function setUploadStatus(message, type) {
  //Sets the upload status message with given text and CSS class.
  const element = document.getElementById('upload-status');
  element.textContent = message;
  element.classList = `upload-status${type ? ' ' + type : ''}`;
}

function handleDragOver(event) {
  //Prevents default browser dragover behavior
  event.preventDefault();
  document.getElementById('upload-drop-zone').classList.add('drag-over');
}

function handleDragLeave(event) {
  //Removes the highlight when the user drags the file out of the drop zone
  document.getElementById('upload-drop-zone').classList.remove('drag-over');
}

function handleDrop(event) {
  //Handles a user dropping a file in the drop zone, verifies it's a .CSV file, and sets it for upload.
  event.preventDefault();
  document.getElementById('upload-drop-zone').classList.remove('drag-over');

  const file = event.dataTransfer.files[0];

  //Only accepts .csv files, reject all else
  if (file && file.name.toLowerCase().endsWith('.csv')) {
    setFile(file);
  } else {
    setUploadStatus('Please drop a .csv file.', 'error');
  }
}

async function uploadCSV() {
  //Uploads the given csv file to the backend.
  //Disables the button during the upload process
  //Refreshs the page after a successful upload to represent if new years have been added
  if (!curFile) return;

  //disables the button during an upload
  const btn = document.getElementById('btn-upload');
  btn.disabled = true;
  btn.textContent = 'Uploading...';
  setUploadStatus('Uploading and importing data...', 'loading');

  const formData = new FormData();
  formData.append('file', curFile);

  // Sends the file to the backend
  try {
    const res = await fetch('/api/admin/upload-csv', {
      method: 'POST',
      body: formData,
    });

    const json = await res.json();

    // Handle the response from the backend if error occurs
    if (!res.ok) {
      setUploadStatus(`Error: ${json.error || 'Upload failed.'}`, 'error');
    } else {
      // If the upload is successful update the UI
      setUploadStatus(
        `Imported ${json.rows_imported} rows from "${json.filename}". Duplicates removed: ${json.duplicates_removed}.`,
        'success'
      );
      clearFile();
      populateYears();  // Refresh dropdowns in case new years were added
    }
  } catch (err) {
    //Handles network errors
    setUploadStatus(`Network error: ${err.message}`, 'error');
    console.error('Admin upload error:', err);
  } finally {
    //enable the button after the upload is complete
    btn.disabled = !curFile;
    btn.textContent = 'Upload CSV';
  }
}