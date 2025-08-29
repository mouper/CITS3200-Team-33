// js/allostaticRegulator.js
// Allostatic Regulation Module for Category-based YouTube Regulation
// 1 unit = 1 hour of watch time in a category


// Default categories with initial values and maximum allowed hours
const DEFAULT_CATEGORIES = {
  "Music":     { watchedHours: 0, msBuffer: 0, maxHours: 10 },
  "Gaming":    { watchedHours: 0, msBuffer: 0, maxHours: 5 },
  "Education": { watchedHours: 0, msBuffer: 0, maxHours: 8 },
  "News":      { watchedHours: 0, msBuffer: 0, maxHours: 6 }
};
const MS_PER_HOUR = 3600000;


// Stores stimulus data for each category, restoring from localStorage if available
let categoryStimulus =
  JSON.parse(localStorage.getItem("categoryStimulus")) ||
  structuredClone(DEFAULT_CATEGORIES);


// Call this whenever the user watches a video, passing the category and milliseconds watched
export function addWatchTime(category, msWatched) {
  if (!categoryStimulus[category]) {
    // Create category entry with default maxHours if it doesn't exist
    categoryStimulus[category] = { watchedHours: 0, msBuffer: 0, maxHours: 5 };
  }
  // Add watched milliseconds to the buffer
  categoryStimulus[category].msBuffer += msWatched;
  // Convert buffered ms to whole hours and increment watchedHours
  while (categoryStimulus[category].msBuffer >= MS_PER_HOUR) {
    categoryStimulus[category].watchedHours += 1;
    categoryStimulus[category].msBuffer -= MS_PER_HOUR;
  }
  saveState();
}


// Returns true if watched hours exceed or equal the maximum allowed for the category
export function shouldRestrictCategory(category) {
  if (!categoryStimulus[category]) return false;
  return categoryStimulus[category].watchedHours >= categoryStimulus[category].maxHours;
}


// Returns an object with watchedHours, msBuffer, and maxHours for each category
export function getCategoryStatus() {
  return { ...categoryStimulus };
}


// Updates the max hours for a specific category
export function setCategoryMaxHours(category, hours) {
  if (!categoryStimulus[category]) return;
  categoryStimulus[category].maxHours = hours;
  saveState();
}


// Resets watched hours and buffer for a specific category
export function resetCategory(category) {
  if (categoryStimulus[category]) {
    categoryStimulus[category].watchedHours = 0;
    categoryStimulus[category].msBuffer = 0;
    saveState();
  }
}


// Resets all categories to their default state
export function resetAllCategories() {
  categoryStimulus = structuredClone(DEFAULT_CATEGORIES);
  saveState();
}


// Persists category data to localStorage
function saveState() {
  localStorage.setItem("categoryStimulus", JSON.stringify(categoryStimulus));
}


// Loads saved data from localStorage if available
(function restoreState() {
  try {
    const saved = JSON.parse(localStorage.getItem("categoryStimulus"));
    if (saved) categoryStimulus = saved;
  } catch {}
})();

// --- Example integration (not part of module, for usage) ---
// Example usage:
// import { addWatchTime, shouldRestrictCategory, getCategoryStatus } from './js/allostaticRegulator.js';
// addWatchTime("Gaming", 1500000);
// if (shouldRestrictCategory("Gaming")) { /* Block Gaming videos */ }
// getCategoryStatus() can be used to display info in the UI.