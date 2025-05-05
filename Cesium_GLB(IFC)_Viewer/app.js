// Initialize Cesium viewer
// Use the default access token which should work for basic functionality
Cesium.Ion.defaultAccessToken = 'a.a.a';

const viewer = new Cesium.Viewer('cesiumContainer', {
  timeline: false,
  animation: false,
  baseLayerPicker: true,
  fullscreenButton: true,
  homeButton: true,
  infoBox: true,
  sceneModePicker: true,
  selectionIndicator: true,
  navigationHelpButton: true
});

// Try to add terrain if available
try {
  if (Cesium.createWorldTerrain) {
    const worldTerrain = Cesium.createWorldTerrain();
    viewer.terrainProvider = worldTerrain;
  }
} catch (e) {
  console.log("Could not load terrain: ", e);
}

// Add Cesium OSM Buildings to the viewer
try {
  const buildingTileset = Cesium.createOsmBuildings();
  viewer.scene.primitives.add(buildingTileset);
} catch (e) {
  console.log("Could not load OSM Buildings: ", e);
}

// Create a default view (Philadelphia)
viewer.camera.flyTo({
  destination: Cesium.Cartesian3.fromDegrees(-71.0349999, 42.213, 1000),
  orientation: {
    heading: 0.0,
    pitch: -Cesium.Math.PI_OVER_FOUR,
    roll: 0.0
  }
});

// Track loaded models for management
let loadedModel = null;
let selectedFile = null;
let currentModelMatrix = null;

// Default Philadelphia coordinates (initial values for the form)
const defaultCoordinates = {
  longitude: -71.0349999,
  latitude: 42.213,
  height: 0,
  heading: 0,
  pitch: 0,
  roll: 0,
  scale: 1.0
};

// Handle file selection
document.getElementById('glbFileInput').addEventListener('change', function(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  // Verify file is GLB
  if (!file.name.toLowerCase().endsWith('.glb')) {
    updateModelInfo('Error: Please select a valid GLB file.');
    return;
  }
  
  selectedFile = file;
  updateModelInfo(`<p>File selected: ${file.name}</p><p>Click "Load GLB File" to place it at the specified coordinates.</p>`);
});

// Handle "Load GLB File" button
document.getElementById('loadGlbFile').addEventListener('click', function() {
  if (!selectedFile) {
    updateModelInfo('Error: Please select a GLB file to load.');
    return;
  }
  
  // Get coordinates from input fields
  const coordinates = getCoordinatesFromInputs();
  
  // Load the GLB file with the specified coordinates
  loadGlbFile(selectedFile, coordinates);
});

// Handle "Apply Position" button - new functionality
document.getElementById('applyPosition').addEventListener('click', function() {
  if (!loadedModel) {
    updateModelInfo('Error: No model loaded to update position.');
    return;
  }
  
  // Get updated coordinates from input fields
  const coordinates = getCoordinatesFromInputs();
  
  // Update model position without reloading
  updateModelPosition(coordinates);
  
  // Update info panel with new coordinates
  updatePositionInfo(coordinates);
});

// Handle "Reset Position" button
document.getElementById('resetPosition').addEventListener('click', function() {
  // Reset coordinate inputs to default values
  document.getElementById('longitude').value = defaultCoordinates.longitude;
  document.getElementById('latitude').value = defaultCoordinates.latitude;
  document.getElementById('height').value = defaultCoordinates.height;
  document.getElementById('heading').value = defaultCoordinates.heading;
  document.getElementById('pitch').value = defaultCoordinates.pitch;
  document.getElementById('roll').value = defaultCoordinates.roll;
  document.getElementById('scale').value = defaultCoordinates.scale;
  
  // If a model is loaded, update its position
  if (loadedModel) {
    updateModelPosition(defaultCoordinates);
    updatePositionInfo(defaultCoordinates);
  }
});

// Handle "Clear Model" button
document.getElementById('clearData').addEventListener('click', function() {
  clearModel();
  // Disable measuring tools when model is cleared
  toggleMeasuringTools(false);
});

// Function to get coordinates from input fields
function getCoordinatesFromInputs() {
  return {
    longitude: parseFloat(document.getElementById('longitude').value),
    latitude: parseFloat(document.getElementById('latitude').value),
    height: parseFloat(document.getElementById('height').value),
    heading: parseFloat(document.getElementById('heading').value),
    pitch: parseFloat(document.getElementById('pitch').value),
    roll: parseFloat(document.getElementById('roll').value),
    scale: parseFloat(document.getElementById('scale').value)
  };
}

// Function to create a model matrix from coordinates
function createModelMatrix(coordinates) {
  // Create a transformation matrix for the model's position and orientation
  const position = Cesium.Cartesian3.fromDegrees(
    coordinates.longitude,
    coordinates.latitude,
    coordinates.height
  );
  
  // Create a heading-pitch-roll rotation
  const headingRadians = Cesium.Math.toRadians(coordinates.heading);
  const pitchRadians = Cesium.Math.toRadians(coordinates.pitch);
  const rollRadians = Cesium.Math.toRadians(coordinates.roll);
  
  // Create the model matrix
  const hpr = new Cesium.HeadingPitchRoll(headingRadians, pitchRadians, rollRadians);
  const orientation = Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
  
  let modelMatrix = Cesium.Matrix4.fromTranslationQuaternionRotationScale(
    position,
    orientation,
    new Cesium.Cartesian3(coordinates.scale, coordinates.scale, coordinates.scale)
  );
  
  return modelMatrix;
}

// New function to update model position without reloading
function updateModelPosition(coordinates) {
  if (!loadedModel) return;
  // Create a new model matrix
  const modelMatrix = createModelMatrix(coordinates);
  // Update the model's modelMatrix property
  loadedModel.modelMatrix = modelMatrix;
  currentModelMatrix = modelMatrix;
  // No camera flyTo here!
}

// New function to update position info in the model info panel
function updatePositionInfo(coordinates) {
  const positionHTML = `
    <p><strong>Position:</strong></p>
    <ul>
      <li>Longitude: ${coordinates.longitude.toFixed(7)}°</li>
      <li>Latitude: ${coordinates.latitude.toFixed(7)}°</li>
      <li>Height: ${coordinates.height.toFixed(2)} m</li>
    </ul>
    <p><strong>Orientation:</strong></p>
    <ul>
      <li>Heading: ${coordinates.heading.toFixed(2)}°</li>
      <li>Pitch: ${coordinates.pitch.toFixed(2)}°</li>
      <li>Roll: ${coordinates.roll.toFixed(2)}°</li>
    </ul>
    <p><strong>Scale:</strong> ${coordinates.scale.toFixed(2)}</p>
  `;
  
  // Update model info with new position data
  document.getElementById('positionInfo').innerHTML = positionHTML;
}

// Function to load a GLB file with specified coordinates
function loadGlbFile(file, coordinates) {
  try {
    // Create a URL for the blob
    const blobUrl = URL.createObjectURL(file);
    // Clear any previously loaded model
    clearModel();
    // Create the model matrix
    const modelMatrix = createModelMatrix(coordinates);
    currentModelMatrix = modelMatrix;
    // Load the model in Cesium
    loadedModel = viewer.scene.primitives.add(
      Cesium.Model.fromGltf({
        url: blobUrl,
        modelMatrix: modelMatrix,
        scale: 1.0 // Scale is handled in the model matrix
      })
    );
    // When the model is ready, zoom to it
    loadedModel.readyPromise.then(() => {
      // Update model info panel
      updateModelInfo(`
        <p><strong>Loaded GLB Model:</strong> ${file.name}</p>
        <p><strong>File Size:</strong> ${formatFileSize(file.size)}</p>
        <div id="positionInfo">
          <p><strong>Position:</strong></p>
          <ul>
            <li>Longitude: ${coordinates.longitude.toFixed(7)}°</li>
            <li>Latitude: ${coordinates.latitude.toFixed(7)}°</li>
            <li>Height: ${coordinates.height.toFixed(2)} m</li>
          </ul>
          <p><strong>Orientation:</strong></p>
          <ul>
            <li>Heading: ${coordinates.heading.toFixed(2)}°</li>
            <li>Pitch: ${coordinates.pitch.toFixed(2)}°</li>
            <li>Roll: ${coordinates.roll.toFixed(2)}°</li>
          </ul>
          <p><strong>Scale:</strong> ${coordinates.scale.toFixed(2)}</p>
        </div>
        <p>Click on model to view properties.</p>
      `);
      // Zoom to the model (fix heading: do NOT add 180)
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          coordinates.longitude,
          coordinates.latitude,
          coordinates.height + 100 // Add some height for better viewing
        ),
        orientation: {
          heading: Cesium.Math.toRadians(coordinates.heading), // Face the model
          pitch: Cesium.Math.toRadians(-30), // Look down at the model
          roll: 0.0
        }
      });
      // Enable measuring tools when model is loaded
      toggleMeasuringTools(true);
    }).catch(error => {
      console.error('Error loading GLB model:', error);
      updateModelInfo(`Error: Could not load GLB file. ${error.message}`);
    });
  } catch (error) {
    console.error('Error loading GLB file:', error);
    updateModelInfo(`Error: Could not load GLB file. ${error.message}`);
  }
}

// Clear loaded model
function clearModel() {
  if (loadedModel) {
    viewer.scene.primitives.remove(loadedModel);
    loadedModel = null;
    currentModelMatrix = null;
  }
  
  updateModelInfo("No model loaded");
  
  // Clean up any active measurements
  clearMeasurements();
}

// Update the model info panel
function updateModelInfo(html) {
  document.getElementById('modelInfo').innerHTML = html;
}

// Format file size in human-readable format
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' bytes';
  else if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
  else return (bytes / 1048576).toFixed(2) + ' MB';
}

// Add model selection capability
const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
handler.setInputAction(function(click) {
  const pickedObject = viewer.scene.pick(click.position);
  
  // If we picked a model
  if (Cesium.defined(pickedObject) && Cesium.defined(pickedObject.primitive) && 
      pickedObject.primitive instanceof Cesium.Model) {
    // For GLB models
    let infoHTML = `<h4>GLB Model Element</h4>`;
    infoHTML += '<ul style="padding-left: 20px;">';
    
    // Get node information if available
    const model = pickedObject.primitive;
    const nodeId = pickedObject.nodeId;
    
    if (Cesium.defined(nodeId)) {
      infoHTML += `<li><strong>Node ID:</strong> ${nodeId}</li>`;
      
      // If we have nodes array in the model, try to get more info
      if (model.gltf && model.gltf.nodes && model.gltf.nodes[nodeId]) {
        const node = model.gltf.nodes[nodeId];
        if (node.name) {
          infoHTML += `<li><strong>Name:</strong> ${node.name}</li>`;
        }
      }
      
      // Show matrix/transform if available
      if (pickedObject.modelMatrix) {
        infoHTML += `<li><strong>Has Position Matrix:</strong> Yes</li>`;
      }
    } else {
      infoHTML += '<li>Limited information available for this element</li>';
    }
    
    infoHTML += '</ul>';
    
    // Append to existing model info rather than replace it
    document.getElementById('modelInfo').innerHTML += infoHTML;
  }
}, Cesium.ScreenSpaceEventType.LEFT_CLICK);

// --- MEASURING TOOLS FUNCTIONALITY ---

// Variables for measurement tools
let measuringMode = null; // Can be 'point', 'distance', 'area' or null
let measurementEntities = [];
let activePoints = [];
let activePolyline = null;
let activePolygon = null;
let measurementClickHandler = null;
let measurementMoveHandler = null;

// Function to toggle measuring tools
function toggleMeasuringTools(enabled) {
  document.getElementById('measuringTools').style.display = enabled ? 'block' : 'none';
  if (!enabled && measuringMode) {
    stopMeasuring();
  }
}

// Setup measurement click handler
function setupMeasurementHandlers() {
  // Remove existing handlers if any
  clearMeasurementHandlers();
  
  // Create new handlers
  measurementClickHandler = handler.setInputAction(function(click) {
    if (!measuringMode) return;
    
    // Get the cartesian position from the click
    const cartesian = viewer.scene.pickPosition(click.position);
    
    // Ignore if not on terrain/globe
    if (!Cesium.defined(cartesian)) return;
    
    handleMeasurementClick(cartesian);
    
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  
  measurementMoveHandler = handler.setInputAction(function(movement) {
    if (!measuringMode || activePoints.length === 0) return;
    
    // Get the cartesian position from the movement
    const cartesian = viewer.scene.pickPosition(movement.endPosition);
    if (!Cesium.defined(cartesian)) return;
    
    updateActiveMeasurement(cartesian);
    
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
}

// Handle measurement click
function handleMeasurementClick(position) {
  if (measuringMode === 'point') {
    // Add point to measure its coordinates
    addPointMeasurement(position);
    
    // For point measurements, end measuring after adding the point
    stopMeasuring();
  } 
  else if (measuringMode === 'distance') {
    // Add point for distance measurement
    addPointToPath(position);
    
    // If we have 2 points, calculate distance
    if (activePoints.length === 2) {
      calculateAndDisplayDistance();
    }
  } 
  else if (measuringMode === 'area') {
    // Add point for area measurement
    addPointToPolygon(position);
    
    // Update area calculation with each click
    if (activePoints.length >= 3) {
      calculateAndDisplayArea();
    }
  }
}

// Start measuring in a specific mode
function startMeasuring(mode) {
  // Clear any existing measurements
  clearMeasurements();
  
  // Set the active measuring mode
  measuringMode = mode;
  
  // Highlight the active button
  document.querySelectorAll('.measure-button').forEach(button => {
    button.classList.remove('active');
  });
  document.getElementById(`measure-${mode}`).classList.add('active');
  
  // Setup handlers for the measurement
  setupMeasurementHandlers();
  
  // Update status text
  let instructions = '';
  if (mode === 'point') {
    instructions = 'Click to place a point and measure coordinates';
  } else if (mode === 'distance') {
    instructions = 'Click to start measuring distance. Click again to end.';
  } else if (mode === 'area') {
    instructions = 'Click to define area corners. Double click to finish.';
  }
  document.getElementById('measurementInfo').innerHTML = instructions;
}

// Stop measuring
function stopMeasuring() {
  measuringMode = null;
  activePoints = [];
  
  // Reset active buttons
  document.querySelectorAll('.measure-button').forEach(button => {
    button.classList.remove('active');
  });
  
  // Clear mouse handlers
  clearMeasurementHandlers();
}

// Clear active measurement handlers
function clearMeasurementHandlers() {
  if (measurementClickHandler) {
    handler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK);
    measurementClickHandler = null;
  }
  if (measurementMoveHandler) {
    handler.removeInputAction(Cesium.ScreenSpaceEventType.MOUSE_MOVE);
    measurementMoveHandler = null;
  }
}

// Clear all measurements
function clearMeasurements() {
  // Remove all measurement entities
  measurementEntities.forEach(entity => {
    viewer.entities.remove(entity);
  });
  measurementEntities = [];
  activePoints = [];
  activePolyline = null;
  activePolygon = null;
  
  // Reset measurement info
  document.getElementById('measurementInfo').innerHTML = 'Select a measurement tool';
  
  // Stop measuring mode
  stopMeasuring();
}

// Add point measurement
function addPointMeasurement(position) {
  // Create a point entity
  const pointEntity = viewer.entities.add({
    position: position,
    point: {
      pixelSize: 10,
      color: Cesium.Color.RED,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2
    },
    label: {
      text: 'Calculating...',
      font: '14px sans-serif',
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      outlineWidth: 2,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      pixelOffset: new Cesium.Cartesian2(0, -10)
    }
  });
  
  measurementEntities.push(pointEntity);
  
  // Calculate and display coordinates
  const cartographic = Cesium.Cartographic.fromCartesian(position);
  const longitude = Cesium.Math.toDegrees(cartographic.longitude).toFixed(7);
  const latitude = Cesium.Math.toDegrees(cartographic.latitude).toFixed(7);
  const height = cartographic.height.toFixed(2);
  
  // Update label
  pointEntity.label.text = `Lon: ${longitude}°\nLat: ${latitude}°\nHeight: ${height}m`;
  
  // Update measurement info
  document.getElementById('measurementInfo').innerHTML = 
    `<strong>Point Coordinates:</strong><br>` +
    `Longitude: ${longitude}°<br>` +
    `Latitude: ${latitude}°<br>` +
    `Height: ${height} m`;
}

// Add point to distance path
function addPointToPath(position) {
  // Create point entity
  const pointEntity = viewer.entities.add({
    position: position,
    point: {
      pixelSize: 10,
      color: Cesium.Color.YELLOW,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2
    }
  });
  
  measurementEntities.push(pointEntity);
  activePoints.push(position);
  
  // If this is the first point
  if (activePoints.length === 1) {
    // Create a polyline that will be updated as we move
    activePolyline = viewer.entities.add({
      polyline: {
        positions: new Cesium.CallbackProperty(function() {
          return activePoints;
        }, false),
        width: 3,
        material: new Cesium.ColorMaterialProperty(Cesium.Color.YELLOW)
      }
    });
    measurementEntities.push(activePolyline);
  }
}

// Add point to area polygon
function addPointToPolygon(position) {
  // Create point entity
  const pointEntity = viewer.entities.add({
    position: position,
    point: {
      pixelSize: 10,
      color: Cesium.Color.GREEN,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2
    }
  });
  
  measurementEntities.push(pointEntity);
  activePoints.push(position);
  
  // If this is the first point
  if (activePoints.length === 1) {
    // Create a polyline to show the boundary
    activePolyline = viewer.entities.add({
      polyline: {
        positions: new Cesium.CallbackProperty(function() {
          return [...activePoints, activePoints[0]]; // Close the loop
        }, false),
        width: 3,
        material: new Cesium.ColorMaterialProperty(Cesium.Color.GREEN)
      }
    });
    measurementEntities.push(activePolyline);
    
    // Create a polygon to show the area
    activePolygon = viewer.entities.add({
      polygon: {
        hierarchy: new Cesium.CallbackProperty(function() {
          return new Cesium.PolygonHierarchy(activePoints);
        }, false),
        material: Cesium.Color.GREEN.withAlpha(0.3),
        outline: true,
        outlineColor: Cesium.Color.GREEN
      }
    });
    measurementEntities.push(activePolygon);
  }
}

// Update active measurement during mouse move
function updateActiveMeasurement(position) {
  if (!measuringMode || activePoints.length === 0) return;
  
  if (measuringMode === 'distance') {
    // Create temporary array with the current points and the mouse position
    const positions = [...activePoints];
    if (positions.length >= 1) {
      positions[positions.length] = position;
      
      // Calculate real-time distance
      if (positions.length === 2) {
        const distance = calculateDistance(positions[0], positions[1]);
        document.getElementById('measurementInfo').innerHTML = 
          `<strong>Distance:</strong> ${distance.toFixed(2)} meters`;
      }
    }
  } 
  else if (measuringMode === 'area') {
    // Create temporary array with the current points and the mouse position
    const positions = [...activePoints, position];
    
    // Calculate real-time area if we have enough points
    if (positions.length >= 3) {
      const area = calculatePolygonArea(positions);
      document.getElementById('measurementInfo').innerHTML = 
        `<strong>Area:</strong> ${formatArea(area)}`;
    }
  }
}

// Calculate distance between two points
function calculateDistance(point1, point2) {
  return Cesium.Cartesian3.distance(point1, point2);
}

// Calculate and display distance
function calculateAndDisplayDistance() {
  if (activePoints.length !== 2) return;
  
  const distance = calculateDistance(activePoints[0], activePoints[1]);
  
  // Create a label at the midpoint
  const midpoint = Cesium.Cartesian3.midpoint(activePoints[0], activePoints[1], new Cesium.Cartesian3());
  
  const labelEntity = viewer.entities.add({
    position: midpoint,
    label: {
      text: `${distance.toFixed(2)} m`,
      font: '14px sans-serif',
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      outlineWidth: 2,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      pixelOffset: new Cesium.Cartesian2(0, -10)
    }
  });
  
  measurementEntities.push(labelEntity);
  
  // Update measurement info
  document.getElementById('measurementInfo').innerHTML = 
    `<strong>Distance:</strong> ${distance.toFixed(2)} meters`;
    
  // End measurement
  stopMeasuring();
}

// Calculate polygon area
function calculatePolygonArea(positions) {
  if (positions.length < 3) return 0;
  
  // Convert 3D cartesian points to cartographics
  const cartographics = positions.map(position => {
    return Cesium.Cartographic.fromCartesian(position);
  });
  
  // Calculate area using a simple algorithm
  // This is a simplified approach and not accurate for large areas due to Earth's curvature
  let area = 0;
  const radiansPerDegree = Math.PI / 180.0;
  
  // Calculate using the Shoelace formula (Gauss's area formula)
  for (let i = 0; i < cartographics.length; i++) {
    const j = (i + 1) % cartographics.length;
    const lon1 = cartographics[i].longitude;
    const lat1 = cartographics[i].latitude;
    const lon2 = cartographics[j].longitude;
    const lat2 = cartographics[j].latitude;
    
    area += (lon2 - lon1) * (2 + Math.sin(lat1) + Math.sin(lat2));
  }
  
  area = Math.abs(area * 6378137.0 * 6378137.0 / 2.0);
  return area;
}

// Calculate and display area
function calculateAndDisplayArea() {
  if (activePoints.length < 3) return;
  
  const area = calculatePolygonArea(activePoints);
  
  // Find centroid of the polygon for label placement
  const centroid = calculateCentroid(activePoints);
  
  // Create label entity
  const labelEntity = viewer.entities.add({
    position: centroid,
    label: {
      text: formatArea(area),
      font: '14px sans-serif',
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      outlineWidth: 2,
      verticalOrigin: Cesium.VerticalOrigin.CENTER,
      horizontalOrigin: Cesium.HorizontalOrigin.CENTER
    }
  });
  
  measurementEntities.push(labelEntity);
  
  // Update measurement info
  document.getElementById('measurementInfo').innerHTML = 
    `<strong>Area:</strong> ${formatArea(area)}`;
}

// Calculate centroid of a polygon
function calculateCentroid(positions) {
  let center = new Cesium.Cartesian3(0, 0, 0);
  positions.forEach(position => {
    center = Cesium.Cartesian3.add(center, position, center);
  });
  return Cesium.Cartesian3.divideByScalar(center, positions.length, center);
}

// Format area in appropriate units
function formatArea(area) {
  if (area < 10000) {
    return `${area.toFixed(2)} m²`;
  } else {
    return `${(area / 1000000).toFixed(4)} km²`;
  }
}

// Initialize measurement tools when document is ready
document.addEventListener('DOMContentLoaded', function() {
  // Initially disable measuring tools until a model is loaded
  toggleMeasuringTools(false);
  
  // Add event listeners for measurement buttons
  document.getElementById('measure-point').addEventListener('click', function() {
    startMeasuring('point');
  });
  
  document.getElementById('measure-distance').addEventListener('click', function() {
    startMeasuring('distance');
  });
  
  document.getElementById('measure-area').addEventListener('click', function() {
    startMeasuring('area');
  });
  
  document.getElementById('measure-clear').addEventListener('click', function() {
    clearMeasurements();
  });

  // Sidebar collapse/expand
  const sidebar = document.getElementById('sidebar');
  const collapseBtn = document.getElementById('sidebarCollapseBtn');
  let collapsed = false;
  collapseBtn.addEventListener('click', function() {
    collapsed = !collapsed;
    sidebar.classList.toggle('collapsed', collapsed);
    collapseBtn.innerText = collapsed ? '⮞' : '⮜';
  });

  // Dark mode toggle
  const darkModeBtn = document.getElementById('darkModeToggle');
  darkModeBtn.addEventListener('click', function() {
    document.body.classList.toggle('dark-mode');
  });

  // Sidebar draggable
  const dragHandle = document.getElementById('sidebarDragHandle');
  let isDragging = false, dragOffsetX = 0, dragOffsetY = 0;
  dragHandle.addEventListener('mousedown', function(e) {
    isDragging = true;
    const rect = sidebar.getBoundingClientRect();
    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;
    document.body.style.userSelect = 'none';
  });
  document.addEventListener('mousemove', function(e) {
    if (!isDragging) return;
    let x = e.clientX - dragOffsetX;
    let y = e.clientY - dragOffsetY;
    // Keep sidebar within window
    x = Math.max(0, Math.min(window.innerWidth - sidebar.offsetWidth, x));
    y = Math.max(0, Math.min(window.innerHeight - sidebar.offsetHeight, y));
    sidebar.style.left = x + 'px';
    sidebar.style.top = y + 'px';
    sidebar.style.position = 'absolute';
  });
  document.addEventListener('mouseup', function() {
    isDragging = false;
    document.body.style.userSelect = '';
  });

  // --- Model Manipulation UI ---
  // Add buttons for Move, Rotate, Scale below Model Placement
  const modelPlacement = document.querySelector('.form-group:nth-of-type(2)');
  if (modelPlacement && !document.getElementById('manipulateGroup')) {
    const manipDiv = document.createElement('div');
    manipDiv.className = 'button-group';
    manipDiv.id = 'manipulateGroup';
    manipDiv.innerHTML = `
      <div class="button secondary" id="moveModelBtn">Move</div>
      <div class="button secondary" id="rotateModelBtn">Rotate</div>
      <div class="button secondary" id="scaleModelBtn">Scale</div>
    `;
    modelPlacement.appendChild(manipDiv);
  }

  // Add event listeners for manipulation buttons
  let manipulationMode = null;
  function setManipulationMode(mode) {
    manipulationMode = mode;
    document.getElementById('moveModelBtn').classList.toggle('active', mode === 'move');
    document.getElementById('rotateModelBtn').classList.toggle('active', mode === 'rotate');
    document.getElementById('scaleModelBtn').classList.toggle('active', mode === 'scale');
    updateModelInfo(`<b>Manipulation Mode:</b> ${mode ? mode.charAt(0).toUpperCase() + mode.slice(1) : 'None'}<br>Use the input fields or future gizmo controls to adjust the model.`);
  }
  document.getElementById('moveModelBtn').addEventListener('click', function() { setManipulationMode('move'); });
  document.getElementById('rotateModelBtn').addEventListener('click', function() { setManipulationMode('rotate'); });
  document.getElementById('scaleModelBtn').addEventListener('click', function() { setManipulationMode('scale'); });
});