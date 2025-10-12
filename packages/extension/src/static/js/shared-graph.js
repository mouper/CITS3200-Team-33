// Shared graph functionality for dashboard and popup
// Version: 1.0.0 - Avoid code duplication

const SERVER_BASE = 'http://127.0.0.1:5050';

class SharedGraph {
  constructor(canvasId, categoryElementId = null, hoursFilter = null) {
    this.canvas = document.getElementById(canvasId);
    this.categoryElement = categoryElementId ? document.getElementById(categoryElementId) : null;
    this.chartInstance = null;
    this.serverBase = SERVER_BASE;
    this.hoursFilter = hoursFilter; // Filter data to last N hours
    
    console.log(`🔍 SharedGraph constructor - Canvas ID: ${canvasId}, Found:`, !!this.canvas, `Hours filter: ${hoursFilter}`);
  }

  async initialize() {
    if (!this.canvas) {
      console.log("❌ Canvas not found:", this.canvas);
      return;
    }

    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
      console.error("❌ Chart.js not loaded");
      return;
    }

    console.log("✅ Initializing shared Chart.js with canvas:", this.canvas.id);

    // Destroy existing chart if it exists
    if (this.chartInstance) {
      this.chartInstance.destroy();
    }

    this.chartInstance = new Chart(this.canvas, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Level',
          data: [],
          borderColor: 'rgba(232, 103, 90, 0.8)',
          backgroundColor: 'rgba(232, 103, 90, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: 'rgba(232, 103, 90, 1)',
          pointBorderColor: 'rgba(232, 103, 90, 1)',
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: {
            top: 20,
            bottom: 50
          }
        },
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: 'Time',
              color: '#F5E8D8',
              font: {
                family: 'Figtree',
                size: 13
              }
            },
            ticks: {
              color: 'rgba(255, 255, 255, 0.6)',
              maxTicksLimit: 6,
              font: {
                family: 'Figtree'
              }
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)',
              display: false
            }
          },
          y: {
            display: true,
            title: {
              display: true,
              text: 'Level',
              color: '#F5E8D8',
              font: {
                family: 'Figtree',
                size: 13
              }
            },
            ticks: {
              color: 'rgba(255, 255, 255, 0.6)',
              callback: function(value) {
                return value.toFixed(2);
              },
              maxTicksLimit: 5,
              font: {
                family: 'Figtree'
              }
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            }
          }
        },
        elements: {
          point: {
            hoverBackgroundColor: 'rgba(232, 103, 90, 1)'
          }
        }
      }
    });
    
    console.log("✅ Shared Chart.js initialized successfully!");
  }

  async updateChart(selectedCategory = null) {
    const category = selectedCategory || (this.categoryElement ? this.categoryElement.textContent : null);
    console.log("📊 Updating shared chart for category:", category);
    console.log("🔍 Chart instance exists:", !!this.chartInstance);
    
    if (!category || category === 'All') {
      console.log("⚠️ No category selected, clearing chart");
      if (this.chartInstance) {
        this.chartInstance.data.labels = [];
        this.chartInstance.data.datasets[0].data = [];
        this.chartInstance.update();
      }
      return;
    }
    
    try {
      // Fetch data and update chart
      console.log(`🌐 Fetching from: ${this.serverBase}/api/stats/category-history?category=${encodeURIComponent(category)}`);
      const response = await fetch(`${this.serverBase}/api/stats/category-history?category=${encodeURIComponent(category)}`);
      console.log("📡 Response status:", response.status);
      
      const result = await response.json();
      console.log("📊 API result:", result);
      
      if (result.success && result.data && result.data.length > 0) {
        console.log("✅ Shared chart updated with", result.data.length, "data points");
        console.log("🔍 Sample data point:", result.data[0]);
        this.updateChartData(result.data);
      } else {
        console.log("⚠️ No data available for this category");
        console.log("🔍 Result details:", { success: result.success, dataLength: result.data?.length, hasData: !!result.data });
        // Clear chart data
        if (this.chartInstance) {
          this.chartInstance.data.labels = [];
          this.chartInstance.data.datasets[0].data = [];
          this.chartInstance.update();
        }
      }
    } catch (error) {
      console.error("❌ Error fetching category history:", error);
      if (this.chartInstance) {
        this.chartInstance.data.labels = [];
        this.chartInstance.data.datasets[0].data = [];
        this.chartInstance.update();
      }
    }
  }

  updateChartData(data) {
    console.log("🔧 updateChartData called with:", data.length, "data points");
    if (!this.chartInstance) {
      console.log("❌ No chart instance available");
      return;
    }

    console.log("🔍 Chart instance exists:", !!this.chartInstance);

    // Filter data by time if hoursFilter is set
    let filteredData = data;
    if (this.hoursFilter) {
      console.log(`🔍 Filtering ${data.length} points to last ${this.hoursFilter} hours...`);
      filteredData = this.filterDataByHours(data, this.hoursFilter);
      console.log(`📊 Filtered data to last ${this.hoursFilter} hours: ${filteredData.length}/${data.length} points`);
      
      // Debug: show time range of filtered data
      if (filteredData.length > 0) {
        const times = filteredData.map(item => item.updated_at);
        console.log(`⏰ Time range: ${times[0]} to ${times[times.length - 1]}`);
        console.log(`📈 Most recent data point: ${data[0]?.updated_at || 'N/A'}`);
        console.log(`🔍 Filtered ${data.length} points to ${filteredData.length} points`);
      } else {
        console.log("⚠️ No data after filtering!");
        console.log(`🔍 Current time: ${new Date().toISOString()}`);
        console.log(`🔍 Sample data times:`, data.slice(0, 3).map(item => item.updated_at));
      }
    } else {
      console.log("📊 No time filter applied, using all data");
    }

    // Process data for Chart.js
    const labels = [];
    const chartData = [];

    // Process actual data points (no artificial starting point)
    filteredData.forEach(item => {
      const timeStr = item.updated_at;
      
      // Check if we have a full datetime or just time
      if (timeStr.includes('T') || timeStr.includes('-')) {
        // Full datetime format with microseconds (e.g., "2025-09-29 15:32:42.020434")
        console.log(`🔍 Parsing datetime: ${timeStr}`);
        
        // Handle microsecond format by removing microseconds before creating Date
        let dateStr = timeStr;
        if (timeStr.includes('.') && timeStr.split(' ').length === 2) {
          // Remove microseconds: "2025-09-29 15:32:42.020434" -> "2025-09-29 15:32:42"
          const [datePart, timePart] = timeStr.split(' ');
          const timeWithoutMicroseconds = timePart.split('.')[0];
          dateStr = `${datePart} ${timeWithoutMicroseconds}`;
        }
        
        const date = new Date(dateStr);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
          console.error(`❌ Invalid date: ${timeStr} (processed: ${dateStr})`);
          // Final fallback: parse manually
          const timePart = timeStr.split(' ')[1];
          if (timePart) {
            const timeWithoutMicroseconds = timePart.split('.')[0];
            const [hours, minutes] = timeWithoutMicroseconds.split(':').map(Number);
            if (this.hoursFilter && this.hoursFilter <= 4) {
              // Popup: show only time
              const timeLabel = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
              labels.push(timeLabel);
            } else {
              // Dashboard: show only time
              const timeLabel = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
              labels.push(timeLabel);
            }
          } else {
            labels.push('00:00');
          }
        } else {
          // Show time only for both dashboard (24h) and popup (4h)
          if (this.hoursFilter && this.hoursFilter <= 4) {
            // Popup: show only time
            const timeLabel = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            labels.push(timeLabel);
          } else {
            // Dashboard: show only time
            const timeLabel = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            labels.push(timeLabel);
          }
        }
      } else {
        // Time-only format (e.g., "14:30:25" or "14:30")
        const [hours, minutes] = timeStr.split(':').map(Number);
        const timeLabel = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
        labels.push(timeLabel);
      }
      
      chartData.push(item.level);
    });

    // Sort by time (now using full timestamps for proper chronological order)
    const combined = labels.map((label, index) => ({
      label: label,
      data: chartData[index],
      time: this.parseTime(filteredData[index].updated_at) // Use original timestamp for sorting
    })).sort((a, b) => a.time - b.time);
    
    console.log("🔍 Chronological sorting check:");
    console.log("📊 First 3 sorted times:", combined.slice(0, 3).map(item => ({
      label: item.label,
      time: new Date(item.time).toISOString()
    })));
    console.log("📊 Last 3 sorted times:", combined.slice(-3).map(item => ({
      label: item.label,
      time: new Date(item.time).toISOString()
    })));

    // Update chart
    console.log("📊 Final labels:", combined.map(item => item.label));
    console.log("📊 Final data:", combined.map(item => item.data));
    
    this.chartInstance.data.labels = combined.map(item => item.label);
    this.chartInstance.data.datasets[0].data = combined.map(item => item.data);
    
    console.log("🔄 Updating chart...");
    this.chartInstance.update();
    console.log("✅ Chart update complete!");
  }

  cleanDateString(dateStr) {
    // Remove microseconds from datetime string for proper Date parsing
    if (dateStr.includes('.') && dateStr.split(' ').length === 2) {
      const [datePart, timePart] = dateStr.split(' ');
      const timeWithoutMicroseconds = timePart.split('.')[0];
      return `${datePart} ${timeWithoutMicroseconds}`;
    }
    return dateStr;
  }

  parseTime(timeStr) {
    // Check if we have a full datetime or just time
    if (timeStr.includes('T') || timeStr.includes('-')) {
      // Full datetime format with microseconds - handle properly
      let dateStr = timeStr;
      if (timeStr.includes('.') && timeStr.split(' ').length === 2) {
        // Remove microseconds: "2025-09-29 15:32:42.020434" -> "2025-09-29 15:32:42"
        const [datePart, timePart] = timeStr.split(' ');
        const timeWithoutMicroseconds = timePart.split('.')[0];
        dateStr = `${datePart} ${timeWithoutMicroseconds}`;
      }
      
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) {
        // Fallback: parse manually from "YYYY-MM-DD HH:MM:SS.microseconds" format
        const [datePart, timePart] = timeStr.split(' ');
        if (timePart) {
          // Remove microseconds if present (e.g., "18:16:09.584677" -> "18:16:09")
          const timeWithoutMicroseconds = timePart.split('.')[0];
          const fallbackDateStr = `${datePart} ${timeWithoutMicroseconds}`;
          const fallbackDate = new Date(fallbackDateStr);
          return fallbackDate.getTime(); // Return full timestamp
        }
        return 0;
      }
      return date.getTime(); // Return full timestamp for proper chronological sorting
    } else {
      // Time-only format (e.g., "14:30:25" or "14:30")
      const [hours, minutes] = timeStr.split(':').map(Number);
      return hours * 60 + minutes;
    }
  }

  filterDataByHours(data, hours) {
    if (data.length === 0) return data;
    
    // Check if we have datetime data (with dates) or time-only data
    const hasDates = data.some(item => 
      item.updated_at.includes('T') || item.updated_at.includes('-')
    );
    
    if (hasDates) {
      // Handle full datetime data with microseconds
      const sortedData = [...data].sort((a, b) => {
        // Handle microseconds by removing them before creating Date objects
        const dateA = this.cleanDateString(a.updated_at);
        const dateB = this.cleanDateString(b.updated_at);
        return new Date(dateB) - new Date(dateA); // Sort descending (newest first)
      });
      
      // Get the most recent data point
      const mostRecentDate = new Date(this.cleanDateString(sortedData[0].updated_at));
      const cutoffTime = new Date(mostRecentDate.getTime() - (hours * 60 * 60 * 1000));
      
      // Filter to only include data within the last N hours from the most recent point
      const filteredData = sortedData.filter(item => {
        const itemDate = new Date(this.cleanDateString(item.updated_at));
        return itemDate >= cutoffTime;
      });
      
      // Return in chronological order (oldest first)
      return filteredData.reverse();
    } else {
      // Handle time-only data (existing logic)
      const sortedData = [...data].sort((a, b) => {
        const timeA = this.parseTime(a.updated_at);
        const timeB = this.parseTime(b.updated_at);
        return timeB - timeA; // Sort descending (newest first)
      });
      
      // Get the most recent data point to establish the time range
      const mostRecentTime = this.parseTime(sortedData[0].updated_at);
      const cutoffMinutes = hours * 60;
      
      // Filter to only include data within the last N hours from the most recent point
      const filteredData = sortedData.filter(item => {
        const itemTime = this.parseTime(item.updated_at);
        const timeDiff = mostRecentTime - itemTime;
        
        // Handle day boundary (if most recent is early in day, check if item is from previous day)
        let actualTimeDiff = timeDiff;
        if (timeDiff < 0) {
          // Most recent time is earlier than item time, item might be from previous day
          actualTimeDiff = (24 * 60) - itemTime + mostRecentTime;
        }
        
        return actualTimeDiff <= cutoffMinutes;
      });
      
      // Return in chronological order (oldest first)
      return filteredData.reverse();
    }
  }

  destroy() {
    if (this.chartInstance) {
      this.chartInstance.destroy();
      this.chartInstance = null;
    }
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SharedGraph;
} else {
  window.SharedGraph = SharedGraph;
}
