
let paneStates = {  //Keep track of pane states
  left: 'none',
  right: 'none',
  top: 'none',
  bottom: 'none',
  single: 'none',
  topLeft: 'none',
  topRight: 'none'
};
let prevWindowType = '';

// Initialize pane states from saved data if available
function initPaneStates() {
  const paneStatesData = document.getElementById('paneStatesData');
  if (paneStatesData && paneStatesData.value) {
    try {
      console.log("Loading pane states from:", paneStatesData.value);
      const savedStates = JSON.parse(paneStatesData.value);

      // Map the saved states to our paneStates object
      Object.keys(savedStates).forEach(key => {
        // Convert keys like 'pane_left' to 'left'
        const paneKey = key.replace('pane_', '');
        if (paneKey in paneStates) {
          paneStates[paneKey] = savedStates[key];
          console.log(`Set ${paneKey} to ${savedStates[key]}`);
        }
      });
    } catch (e) {
      console.error('Error parsing pane states:', e);
    }
  }
}

// Toggle function: clicking a glass cycles through its opening states.
function togglePane(paneId) {
    const states = ['none', 'left', 'right', 'casement-left', 'casement-right', 'awning', 'awning-down'];
    const currentIndex = states.indexOf(paneStates[paneId]);
    paneStates[paneId] = states[(currentIndex + 1) % states.length];
    updateWindow();
}

function updateWindow() {
  const windowType = document.getElementById('windowType').value;
    if (windowType !== prevWindowType) {
      // Reset all pane states when the window type changes
      Object.keys(paneStates).forEach(key => paneStates[key] = 'none');
      prevWindowType = windowType;
    }

  // The sliders now represent outer dimensions.
  const totalHeight = parseInt(document.getElementById('height').value);
  const totalWidth  = parseInt(document.getElementById('width').value);
  const bottomOuter = parseInt(document.getElementById('bottomHeight').value);
  const leftOuter   = parseInt(document.getElementById('leftWidth').value);

  // Update the slider text displays.
  document.getElementById('heightValue').textContent = totalHeight;
  document.getElementById('widthValue').textContent  = totalWidth;
  document.getElementById('bottomHeightValue').textContent = bottomOuter;
  document.getElementById('leftWidthValue').textContent    = leftOuter;

  // Show or hide the bottom and left controls based on window type.
  const bottomHeightControl = document.getElementById('bottomHeight');
  const bottomHeightLabel   = document.getElementById('bottomHeightLabel');
  const leftWidthControl    = document.getElementById('leftWidth');
  const leftWidthLabel      = document.getElementById('leftWidthLabel');

  if (windowType === 'single-pane') {
    bottomHeightControl.style.display = 'none';
    bottomHeightLabel.style.display   = 'none';
    leftWidthControl.style.display    = 'none';
    leftWidthLabel.style.display      = 'none';
  } else if (windowType === 'two-pane') {
    bottomHeightControl.style.display = 'none';
    bottomHeightLabel.style.display   = 'none';
    leftWidthControl.style.display    = 'inline';
    leftWidthLabel.style.display      = 'inline';
  } else if (windowType === 'two-pane-vertical') {
    bottomHeightControl.style.display = 'inline';
    bottomHeightLabel.style.display   = 'inline';
    leftWidthControl.style.display    = 'none';
    leftWidthLabel.style.display      = 'none';
  } else if (windowType === 'three-pane') {
    // In three-pane mode, both bottom and left controls are used.
    bottomHeightControl.style.display = 'inline';
    bottomHeightLabel.style.display   = 'inline';
    leftWidthControl.style.display    = 'inline';
    leftWidthLabel.style.display      = 'inline';
  }

    // Prepare the parameters for the SVG generation request
    const params = {
        window_type: windowType,
        total_height: totalHeight,
        total_width: totalWidth,
        bottom_height: bottomOuter,
        left_width: leftOuter,
        pane_states: {}  // Initialize an empty object for pane states
    };

    // Populate pane_states with the current states, prefixing keys as needed
    for (const key in paneStates) {
        params.pane_states[`pane_${key}`] = paneStates[key];
    }

    // Fetch the SVG from the server
    fetch('/generate_window_svg', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(params)
    })
    .then(response => response.json())
    .then(data => {
        if (data.svg) {
            const svgContainer = document.getElementById('windowSVG');
            // Set the SVG content
            svgContainer.innerHTML = data.svg;
            
            // Set viewBox attribute to ensure proper scaling
            const svgElement = svgContainer.querySelector('svg');
            if (svgElement) {
                // Copy viewBox from inner SVG to container
                const viewBox = svgElement.getAttribute('viewBox');
                svgContainer.setAttribute('viewBox', viewBox);
                
                // Remove the inner SVG's viewBox to prevent double scaling
                svgElement.removeAttribute('viewBox');
                
                // Extract SVG content and replace the container's content
                svgContainer.innerHTML = svgElement.innerHTML;
            }

            // Re-attach click event listeners to glass elements
            // Get all glass elements
            const glassElements = svgContainer.querySelectorAll('.glass');
            
            // Single Pane
            if (windowType === "single-pane" && glassElements.length === 1) {
                glassElements[0].addEventListener('click', () => togglePane('single'));
            }
            // Two Pane
            else if (windowType === "two-pane" && glassElements.length === 2) {
                glassElements[0].addEventListener('click', () => togglePane('left'));
                glassElements[1].addEventListener('click', () => togglePane('right'));
            }
            // Two Pane Vertical
            else if (windowType === "two-pane-vertical" && glassElements.length === 2) {
                glassElements[0].addEventListener('click', () => togglePane('top'));
                glassElements[1].addEventListener('click', () => togglePane('bottom'));
            }
            // Three Pane
            else if (windowType === "three-pane" && glassElements.length === 3) {
                glassElements[0].addEventListener('click', () => togglePane('topLeft'));
                glassElements[1].addEventListener('click', () => togglePane('topRight'));
                glassElements[2].addEventListener('click', () => togglePane('bottom'));
            }
        } else {
            console.error('Error fetching SVG:', data.error);
        }
    })
    .catch(error => console.error('Error fetching SVG:', error));
}

// Save window function
function saveWindow() {
  // Get form data
  const form = document.getElementById('windowForm');
  const formData = new FormData(form);

  // Convert to JSON object
  const windowData = {};
  formData.forEach((value, key) => {
    // Convert numeric values to integers
    if (['total_height', 'total_width', 'bottom_height', 'left_width'].includes(key)) {
      windowData[key] = parseInt(value);
    } else {
      windowData[key] = value;
    }
  });

  // Add pane states to the form data
  Object.keys(paneStates).forEach(key => {
     // Only add non-default pane states
    if (paneStates[key] !== 'none'){
      windowData[`pane_${key}`] = paneStates[key];
    }
  });

  // Log the data being sent to verify pane states are included
  console.log("Sending window data:", windowData);

  // Send data to server
  fetch('/save_window', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(windowData)
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      showMessage('Window saved successfully!', true);
      // If this was a new window, update the form with the new ID
      if (!document.getElementById('windowId').value) {
        document.getElementById('windowId').value = data.window_id;
      }
    } else {
      showMessage('Error: ' + (data.message || 'Unknown error'), false);
    }
  })
  .catch(error => {
    showMessage('Error saving window: ' + error, false);
  });
}

// Show message function
function showMessage(message, isSuccess) {
  const messageDiv = document.getElementById('message');
  messageDiv.textContent = message;
  messageDiv.className = isSuccess ? 'success' : 'error';
  messageDiv.style.display = 'block';

  // Hide message after 5 seconds
  setTimeout(() => {
    messageDiv.style.display = 'none';
  }, 5000);
}

// Export SVG function (remains unchanged)
function exportSVG() {
  const svgData = document.getElementById('windowSVG').outerHTML;
  const svgBlob = new Blob([svgData], {type: 'image/svg+xml;charset=utf-8'});
  const svgUrl = URL.createObjectURL(svgBlob);

  const downloadLink = document.createElement('a');
  downloadLink.href = svgUrl;
  downloadLink.download = 'window_design.svg';
  document.body.appendChild(downloadLink);
  downloadLink.click();
  document.body.removeChild(downloadLink);
}

function editValue(sliderId, min, max, step) {
  const slider = document.getElementById(sliderId);
  let value = prompt(`Enter new value (${min}-${max}):`, slider.value);
  if (value === null) return; // User canceled
  value = parseInt(value);
  if (isNaN(value)) {
    alert("Please enter a valid number");
    return;
  }
  // Round to nearest step and clamp between min/max
  value = Math.round(value / step) * step;
  value = Math.max(min, Math.min(max, value));
  slider.value = value;
  updateWindow();
}

// Initialize prevWindowType when the page loads
document.addEventListener('DOMContentLoaded', function() {
  prevWindowType = document.getElementById('windowType').value;
    // Initialize pane states from saved data
    initPaneStates();
  // Initial render
  updateWindow();
});
