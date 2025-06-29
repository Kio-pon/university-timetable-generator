// timetable_viewer.js

let currentCalendar = null;
let allTimetables = [];

document.addEventListener("DOMContentLoaded", function () {
  generateTimetables();
});

function goBack() {
  window.location.href = "/";
}

async function generateTimetables() {
  document.getElementById("loading-section").style.display = "block";

  try {
    const response = await fetch("/generate", {
      method: "POST",
    });

    const result = await response.json();
    document.getElementById("loading-section").style.display = "none";

    if (result.success && result.count > 0) {
      displayResults(result);
      document.getElementById("results-section").style.display = "block";
    } else {
      document.getElementById("no-results-section").style.display = "block";
    }
  } catch (error) {
    document.getElementById("loading-section").style.display = "none";
    document.getElementById("no-results-section").style.display = "block";
    console.error("Error generating timetables:", error);
  }
}

function displayResults(result) {
  allTimetables = result.timetables;
  const container = document.getElementById("resultsContainer");

  let html = `
          <div class="alert alert-success" id="success-banner" style="transition: opacity 0.7s ease;">
              <h5><i class="fas fa-check-circle"></i> Success! 🎉</h5>
              <p>Generated <strong>${result.count}</strong> valid timetable${
    result.count > 1 ? "s" : ""
  } with perfect time positioning!</p>
              <p class="mb-0"><strong>👆 Click on a combination below to view the timetable:</strong></p>
          </div>

          <div class="combination-tabs">
      `;

  result.timetables.forEach((timetable, index) => {
    html += `
              <div class="combination-tab" onclick="switchTimetable(${index})">
                  <i class="fas fa-calendar-alt me-2"></i>Combination ${
                    index + 1
                  }
                  <div class="small mt-1">${
                    timetable.courses.length
                  } courses</div>
              </div>
          `;
  });

  html += `
          </div>

          <div class="calendar-container" style="display: none;">
              <div class="calendar-header">
                  <h4 class="calendar-title">
                      <i class="fas fa-calendar-week me-2"></i>
                      <span id="calendar-combination-title">Select a combination above</span>
                  </h4>
                  <div class="calendar-stats">
                      <div class="stat-item">
                          <i class="fas fa-book"></i>
                          <span id="calendar-courses-count">- courses</span>
                      </div>
                      <div class="stat-item">
                          <i class="fas fa-clock"></i>
                          <span id="calendar-days-count">- days</span>
                      </div>
                  </div>
              </div>
              <div class="toggle-panel">
                  <h5><i class="fas fa-cog me-2"></i>Display Options</h5>
                  <div class="toggle-controls">
                      <div class="toggle-item">
                          <label class="toggle-switch">
                              <input type="checkbox" id="showCourseCode" checked>
                              <span class="slider round"></span>
                          </label>
                          <span class="toggle-label">Course Code</span>
                      </div>
                      <div class="toggle-item">
                          <label class="toggle-switch">
                              <input type="checkbox" id="showInstructor">
                              <span class="slider round"></span>
                          </label>
                          <span class="toggle-label">Instructor</span>
                      </div>
                      <div class="toggle-item">
                          <label class="toggle-switch">
                              <input type="checkbox" id="showLocation">
                              <span class="slider round"></span>
                          </label>
                          <span class="toggle-label">Location</span>
                      </div>
                  </div>
              </div>
              <div id="calendar"></div>
          </div>
      `;

  container.innerHTML = html;

  // Fade out the success banner after 3 seconds
  setTimeout(function () {
    const banner = document.getElementById("success-banner");
    if (banner) {
      banner.style.opacity = "0";
      setTimeout(function () {
        banner.style.display = "none";
      }, 700);
    }
  }, 3000);
}

function switchTimetable(index) {
  const calendarContainer = document.querySelector(".calendar-container");
  if (calendarContainer) {
    calendarContainer.style.display = "block";
  }
  document.querySelectorAll(".combination-tab").forEach((tab, i) => {
    if (i === index) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });
  initializeCalendar(index);
}

function initializeCalendar(timetableIndex) {
  const timetable = allTimetables[timetableIndex];
  window.currentTimetableData = timetable;
  document.getElementById(
    "calendar-combination-title"
  ).textContent = `Combination ${timetableIndex + 1}`;
  document.getElementById(
    "calendar-courses-count"
  ).textContent = `${timetable.courses.length} courses`;
  const daysUsed = new Set();
  Object.keys(timetable.schedule).forEach((day) => {
    if (timetable.schedule[day].length > 0) {
      daysUsed.add(day);
    }
  });
  document.getElementById(
    "calendar-days-count"
  ).textContent = `${daysUsed.size} days`;
  const events = convertTimetableToEvents(timetable);
  if (currentCalendar) {
    currentCalendar.destroy();
  }
  const calendarEl = document.getElementById("calendar");
  currentCalendar = new FullCalendar.Calendar(calendarEl, {
    initialView: "timeGridWeek",
    headerToolbar: false,
    events: events,
    slotMinTime: "08:00:00",
    slotMaxTime: "19:00:00",
    slotDuration: "00:15:00",
    slotLabelInterval: "01:00:00",
    height: "auto",
    expandRows: true,
    nowIndicator: false,
    allDaySlot: false,
    dayHeaderFormat: { weekday: "long" },
    weekends: false,
    firstDay: 1,
    hiddenDays: [0, 6],
    initialDate: "2025-01-06",
    validRange: {
      start: "2025-01-06",
      end: "2025-01-11",
    },
    dayHeaderContent: function (arg) {
      const dayNames = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
      ];
      return dayNames[arg.date.getDay()];
    },
    eventContent: function (arg) {
      return { html: arg.event.title };
    },
    eventDidMount: function (info) {
      const course = info.event.extendedProps;
      const backgroundColor = info.event.backgroundColor;
      const darkerColor = getCourseColor(course.courseCode, true);
      info.el.style.background = `linear-gradient(135deg, ${backgroundColor}, ${darkerColor})`;
      info.el.setAttribute(
        "title",
        `📚 ${course.title}\n` +
          `📝 ${course.courseCode} ${course.section}\n` +
          `👨‍🏫 ${course.instructor}\n` +
          `🏫 ${course.room}\n` +
          `⏰ ${course.timeSlot}`
      );
      const courseType = getCourseType(course.courseCode);
      info.el.classList.add(`event-${courseType}`);
    },
    eventClick: function (info) {
      const course = info.event.extendedProps;
      showCourseModal(course, info.event);
    },
    windowResize: function () {
      currentCalendar.updateSize();
    },
  });
  currentCalendar.render();
  setupToggleListeners();
}

function convertTimetableToEvents(timetable) {
  const events = [];
  const genericWeekStart = new Date(2025, 0, 6);
  Object.keys(timetable.schedule).forEach((day) => {
    if (timetable.schedule[day].length > 0) {
      timetable.schedule[day].forEach((classInfo) => {
        const dayIndex = getDayIndex(day);
        if (dayIndex === -1) return;
        const eventDate = new Date(genericWeekStart);
        eventDate.setDate(genericWeekStart.getDate() + dayIndex);
        const startDateTime = parseTimeString(classInfo.start, eventDate);
        const endDateTime = parseTimeString(classInfo.end, eventDate);
        if (startDateTime && endDateTime) {
          const eventTitle = buildEventTitle(classInfo);
          events.push({
            title: eventTitle.html,
            start: startDateTime,
            end: endDateTime,
            backgroundColor: getCourseColor(classInfo.course),
            borderColor: getCourseColor(classInfo.course, true),
            extendedProps: {
              courseCode: classInfo.course,
              section: classInfo.section,
              title: classInfo.title,
              instructor: classInfo.instructor,
              room: classInfo.room,
              day: day,
              timeSlot: classInfo.time,
              textTitle: eventTitle.text,
            },
          });
        }
      });
    }
  });
  return events;
}

function buildEventTitle(classInfo) {
  let title = classInfo.title || classInfo.course;
  const showCourseCode =
    document.getElementById("showCourseCode")?.checked || false;
  const showInstructor =
    document.getElementById("showInstructor")?.checked || false;
  const showLocation =
    document.getElementById("showLocation")?.checked || false;
  let details = [];
  if (showCourseCode) {
    title = `${classInfo.title} (${classInfo.course} - ${classInfo.section})`;
  }
  
  if (showInstructor && classInfo.instructor) {
    details.push(`👨‍🏫 ${classInfo.instructor}`);
  }
  if (showLocation && classInfo.room) {
    details.push(`📍 ${classInfo.room}`);
  }
  const timeDisplay = `${classInfo.start} - ${classInfo.end}`;
  return {
    text: `${timeDisplay}\n${title}${
      details.length > 0 ? "\n" + details.join("\n") : ""
    }`,
    html: `<div class="event-time-big">${timeDisplay}</div><div class="event-title">${title}</div>${details
      .map((detail) => `<div class="event-detail">${detail}</div>`)
      .join("")}`,
  };
}

function setupToggleListeners() {
  const toggles = ["showCourseCode", "showInstructor", "showLocation"];
  toggles.forEach((toggleId) => {
    const toggle = document.getElementById(toggleId);
    if (toggle) {
      toggle.addEventListener("change", function () {
        if (currentCalendar && window.currentTimetableData) {
          const newEvents = convertTimetableToEvents(
            window.currentTimetableData
          );
          currentCalendar.removeAllEvents();
          currentCalendar.addEventSource(newEvents);
        }
      });
    }
  });
}

function getCourseType(courseCode) {
  const code = courseCode.toLowerCase();
  if (code.includes("core")) return "core";
  if (code.includes("cs")) return "cs";
  if (code.includes("ee") || code.includes("ce")) return "ee";
  if (code.includes("phy")) return "phy";
  if (code.includes("math")) return "math";
  if (code.includes("mus")) return "mus";
  if (code.includes("bio")) return "bio";
  if (code.includes("com")) return "com";
  if (code.includes("sdp")) return "sdp";
  if (code.includes("lang")) return "lang";
  return "default";
}

function getCourseColor(courseCode, isDark = false) {
  return generatePastelColor(courseCode, isDark);
}

function generatePastelColor(courseCode, isDark = false) {
  let hash = 0;
  for (let i = 0; i < courseCode.length; i++) {
    hash = courseCode.charCodeAt(i) + ((hash << 5) - hash);
  }
  const pastelColors = [
    { light: "#A8DADC", dark: "#7FB3D6" },
    { light: "#B8E6E8", dark: "#88C1C4" },
    { light: "#C7CEDB", dark: "#9FA8B8" },
    { light: "#E0F2F1", dark: "#B2DFDB" },
    { light: "#E1F5FE", dark: "#B3E5FC" },
    { light: "#F0F8FF", dark: "#D6ECFF" },
    { light: "#D4E6B7", dark: "#AECF8D" },
    { light: "#E8F5E8", dark: "#C8E6C8" },
    { light: "#C8E6C8", dark: "#A4D4A4" },
    { light: "#F0F8E8", dark: "#D4E8C4" },
    { light: "#E8F5E8", dark: "#C5E1C5" },
    { light: "#F1F8E9", dark: "#DCEDC8" },
    { light: "#F1C0C8", dark: "#E699A3" },
    { light: "#FFE4E1", dark: "#FFD0CC" },
    { light: "#FFF0F5", dark: "#FFE4F0" },
    { light: "#FFEBEE", dark: "#FFCDD2" },
    { light: "#F8BBD9", dark: "#F48FB1" },
    { light: "#FCE4EC", dark: "#F8BBD9" },
    { light: "#F4D1AE", dark: "#EABC8B" },
    { light: "#FFE4B5", dark: "#F0D085" },
    { light: "#FFEFD5", dark: "#FFE0B2" },
    { light: "#FFF8DC", dark: "#F5DEB3" },
    { light: "#FFEBCD", dark: "#FFD54F" },
    { light: "#FFEAA7", dark: "#FDCB6E" },
    { light: "#E6E6FA", dark: "#D8D8F0" },
    { light: "#F0E6FF", dark: "#E0D0FF" },
    { light: "#E6D7FF", dark: "#D1BFFF" },
    { light: "#DDA0DD", dark: "#C485C4" },
    { light: "#E8DAEF", dark: "#D7BDE2" },
    { light: "#F3E5F5", dark: "#E1BEE7" },
    { light: "#E8C5A0", dark: "#D4A574" },
    { light: "#F5DEB3", dark: "#E6C488" },
    { light: "#FAEBD7", dark: "#E8D4AA" },
    { light: "#FDF6E3", dark: "#F7E9C1" },
    { light: "#F5F5DC", dark: "#EEEEDC" },
    { light: "#F0E68C", dark: "#DAA520" },
    { light: "#F8F8FF", dark: "#E8E8F5" },
    { light: "#E6F3FF", dark: "#CCE7FF" },
    { light: "#E0E6FF", dark: "#C7D2FF" },
    { light: "#F0F4F8", dark: "#E2E8F0" },
    { light: "#F7FAFC", dark: "#EDF2F7" },
    { light: "#E2E8F0", dark: "#CBD5E0" },
    { light: "#FFFACD", dark: "#F0E68C" },
    { light: "#FFEFD5", dark: "#FFE0B2" },
    { light: "#FFF8DC", dark: "#F5DEB3" },
    { light: "#FFFFE0", dark: "#FFFF99" },
    { light: "#F0E68C", dark: "#DAA520" },
    { light: "#FAFAD2", dark: "#F0E68C" },
    { light: "#E6F7FF", dark: "#BAE7FF" },
    { light: "#F6FFED", dark: "#D9F7BE" },
    { light: "#FFF7E6", dark: "#FFE7BA" },
    { light: "#FFF1F0", dark: "#FFD6CC" },
    { light: "#F9F0FF", dark: "#EFDBFF" },
    { light: "#FCFCFC", dark: "#F5F5F5" },
  ];
  const colorIndex = Math.abs(hash) % pastelColors.length;
  const selectedColor = pastelColors[colorIndex];
  return isDark ? selectedColor.dark : selectedColor.light;
}

function getDayIndex(dayName) {
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
  return days.indexOf(dayName);
}

function parseTimeString(timeStr, date) {
  if (!timeStr || !date) return null;
  try {
    const cleanTime = timeStr.trim();
    let hour, minute;
    if (cleanTime.includes("AM") || cleanTime.includes("PM")) {
      const [time, period] = cleanTime.split(" ");
      const [hourStr, minuteStr] = time.split(":");
      hour = parseInt(hourStr);
      minute = parseInt(minuteStr) || 0;
      if (period === "PM" && hour !== 12) {
        hour += 12;
      } else if (period === "AM" && hour === 12) {
        hour = 0;
      }
    } else {
      const [hourStr, minuteStr] = cleanTime.split(":");
      hour = parseInt(hourStr);
      minute = parseInt(minuteStr) || 0;
    }
    const dateTime = new Date(date);
    dateTime.setHours(hour, minute, 0, 0);
    return dateTime;
  } catch (error) {
    console.error("Error parsing time:", timeStr, error);
    return null;
  }
}

function showCourseModal(course, event) {
  const startTime = event.start.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  const endTime = event.end.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  alert(
    `📚 Course Details\n\n` +
      `Title: ${course.title}\n` +
      `Course: ${course.courseCode}\n` +
      `Section: ${course.section}\n` +
      `👨‍🏫 Instructor: ${course.instructor}\n` +
      `🏫 Room: ${course.room}\n` +
      `📅 Day: ${course.day}\n` +
      `⏰ Time: ${startTime} - ${endTime}`
  );
}
