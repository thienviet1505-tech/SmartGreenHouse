// ============================================================
// GreenhouseScene — Realistic glass greenhouse 3D model
// Metal frame grid + glass panels + concrete base + sensors
// ============================================================

import * as THREE from 'three';

/* ---- helper: create a tube/bar ---- */
function bar(scene, mat, x, y, z, sx, sy, sz) {
  const g = new THREE.BoxGeometry(sx, sy, sz);
  const m = new THREE.Mesh(g, mat);
  m.position.set(x, y, z);
  m.castShadow = true;
  m.receiveShadow = true;
  scene.add(m);
  return m;
}

/* ---- helper: create text sprite for labels ---- */
function makeLabel(text, color = '#ffffff') {
  const canvas = document.createElement('canvas');
  const sz = 256;
  canvas.width = sz;
  canvas.height = 80;
  const ctx = canvas.getContext('2d');
  ctx.font = 'bold 28px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  // background pill
  const tw = ctx.measureText(text).width + 24;
  const cx = sz / 2, cy = 40;
  ctx.fillStyle = 'rgba(0,0,0,0.65)';
  ctx.beginPath();
  const rx = cx - tw / 2, ry = cy - 18, rw = tw, rh = 36, rr = 10;
  if (ctx.roundRect) {
    ctx.roundRect(rx, ry, rw, rh, rr);
  } else {
    ctx.moveTo(rx + rr, ry);
    ctx.lineTo(rx + rw - rr, ry); ctx.arcTo(rx + rw, ry, rx + rw, ry + rr, rr);
    ctx.lineTo(rx + rw, ry + rh - rr); ctx.arcTo(rx + rw, ry + rh, rx + rw - rr, ry + rh, rr);
    ctx.lineTo(rx + rr, ry + rh); ctx.arcTo(rx, ry + rh, rx, ry + rh - rr, rr);
    ctx.lineTo(rx, ry + rr); ctx.arcTo(rx, ry, rx + rr, ry, rr);
  }
  ctx.fill();
  ctx.fillStyle = color;
  ctx.fillText(text, cx, cy);

  const tex = new THREE.CanvasTexture(canvas);
  tex.minFilter = THREE.LinearFilter;
  const mat = new THREE.SpriteMaterial({ map: tex, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(0.5, 0.16, 1);
  return sprite;
}

export class GreenhouseScene {
  constructor(canvas, model) {
    this.canvas = canvas;
    this.model = model;
    this._disposed = false;

    // ---- Renderer ----
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;

    // ---- Scene ----
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x87ceeb);

    // ---- Camera ----
    this.camera = new THREE.PerspectiveCamera(50, 2, 0.05, 200);

    // ---- Orbit ----
    this.theta = Math.PI * 0.3;
    this.phi = Math.PI * 0.3;
    this.radius = 5;
    this.target = new THREE.Vector3(0, 0, 0);
    this._setupControls();

    // ---- Lights (persistent) ----
    this.ambientLight = new THREE.AmbientLight(0xffffff, 0.35);
    this.scene.add(this.ambientLight);
    this.hemiLight = new THREE.HemisphereLight(0x87ceeb, 0x4a3520, 0.3);
    this.scene.add(this.hemiLight);

    // Sun
    const sunGeo = new THREE.SphereGeometry(0.4, 16, 16);
    const sunMat = new THREE.MeshBasicMaterial({ color: 0xffee88 });
    this.sun = new THREE.Mesh(sunGeo, sunMat);
    this.scene.add(this.sun);

    this.sunLight = new THREE.DirectionalLight(0xffffff, 1);
    this.sunLight.castShadow = true;
    this.sunLight.shadow.mapSize.width = 1024;
    this.sunLight.shadow.mapSize.height = 1024;
    this.scene.add(this.sunLight);
    this.scene.add(this.sunLight.target);

    // ---- Build greenhouse ----
    this.ghGroup = new THREE.Group();
    this.scene.add(this.ghGroup);
    this._buildGreenhouse();

    // ---- Clouds (separate from ghGroup so they persist across rebuild) ----
    this.clouds = [];
    this._buildClouds();

    this._updateCamera();
    this._handleResize();
  }

  // ==================================================================
  // Rebuild when dimensions change
  // ==================================================================
  rebuild() {
    // Clear old greenhouse group
    this.ghGroup.traverse(obj => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
        else obj.material.dispose();
      }
    });
    this.ghGroup.clear();
    this._buildGreenhouse();
  }

  _buildGreenhouse() {
    const L = this.model.length;
    const W = this.model.width;
    const H = this.model.height;
    const g = this.ghGroup;

    // Reusable materials
    const frameMat = new THREE.MeshStandardMaterial({
      color: 0xd8d8d0, roughness: 0.35, metalness: 0.6
    });
    const frameDarkMat = new THREE.MeshStandardMaterial({
      color: 0x7a7a72, roughness: 0.4, metalness: 0.5
    });
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0xd8f0ee,
      transparent: true,
      opacity: 0.18,
      transmission: 0.75,
      roughness: 0.05,
      metalness: 0.0,
      side: THREE.DoubleSide,
      clearcoat: 0.6,
      clearcoatRoughness: 0.1,
    });
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x505050, roughness: 0.85, metalness: 0.1
    });

    // Frame bar size
    const fb = Math.min(L, W, H) * 0.018;     // frame thickness
    const fb2 = fb * 0.7;                       // secondary frame
    const baseH = H * 0.1;                      // concrete base height

    // ---- Ground ----
    const groundGeo = new THREE.PlaneGeometry(30, 30);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x6a9a55, roughness: 0.9 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(L / 2, -0.01, W / 2);
    ground.receiveShadow = true;
    g.add(ground);

    // ---- Concrete base ----
    // Front/back base walls
    bar(g, baseMat, L / 2, baseH / 2, 0, L + fb * 2, baseH, fb * 3);
    bar(g, baseMat, L / 2, baseH / 2, W, L + fb * 2, baseH, fb * 3);
    // Left/right base walls
    bar(g, baseMat, 0, baseH / 2, W / 2, fb * 3, baseH, W);
    bar(g, baseMat, L, baseH / 2, W / 2, fb * 3, baseH, W);

    // ---- Vertical corner posts ----
    const postH = H - baseH;
    const postY = baseH + postH / 2;
    bar(g, frameMat, 0, postY, 0, fb, postH, fb);
    bar(g, frameMat, L, postY, 0, fb, postH, fb);
    bar(g, frameMat, 0, postY, W, fb, postH, fb);
    bar(g, frameMat, L, postY, W, fb, postH, fb);

    // ---- Top horizontal beams ----
    bar(g, frameMat, L / 2, H, 0, L, fb, fb);
    bar(g, frameMat, L / 2, H, W, L, fb, fb);
    bar(g, frameMat, 0, H, W / 2, fb, fb, W);
    bar(g, frameMat, L, H, W / 2, fb, fb, W);

    // ---- Wall subdivisions ----
    // Determine number of vertical studs per wall
    const nDivL = Math.max(1, Math.round(L / 0.5)); // every ~0.5m
    const nDivW = Math.max(1, Math.round(W / 0.5));
    const hDivs = Math.max(1, Math.round((H - baseH) / 0.5)); // horizontal divisions

    // Front & back walls (along X)
    for (let i = 1; i < nDivL; i++) {
      const x = (i / nDivL) * L;
      bar(g, frameMat, x, postY, 0, fb2, postH, fb2);
      bar(g, frameMat, x, postY, W, fb2, postH, fb2);
    }
    for (let j = 1; j < hDivs; j++) {
      const y = baseH + (j / hDivs) * postH;
      bar(g, frameMat, L / 2, y, 0, L, fb2, fb2);
      bar(g, frameMat, L / 2, y, W, L, fb2, fb2);
    }

    // Left & right walls (along Z)
    for (let i = 1; i < nDivW; i++) {
      const z = (i / nDivW) * W;
      bar(g, frameMat, 0, postY, z, fb2, postH, fb2);
      bar(g, frameMat, L, postY, z, fb2, postH, fb2);
    }
    for (let j = 1; j < hDivs; j++) {
      const y = baseH + (j / hDivs) * postH;
      bar(g, frameMat, 0, y, W / 2, fb2, fb2, W);
      bar(g, frameMat, L, y, W / 2, fb2, fb2, W);
    }

    // ---- Roof frame beams ----
    for (let i = 1; i < nDivL; i++) {
      const x = (i / nDivL) * L;
      bar(g, frameMat, x, H + fb / 2, W / 2, fb2, fb2, W);
    }
    for (let i = 1; i < nDivW; i++) {
      const z = (i / nDivW) * W;
      bar(g, frameMat, L / 2, H + fb / 2, z, L, fb2, fb2);
    }
    // Roof edge beams
    bar(g, frameMat, L / 2, H + fb / 2, 0, L + fb, fb, fb);
    bar(g, frameMat, L / 2, H + fb / 2, W, L + fb, fb, fb);
    bar(g, frameMat, 0, H + fb / 2, W / 2, fb, fb, W);
    bar(g, frameMat, L, H + fb / 2, W / 2, fb, fb, W);

    // ---- Glass panels ----
    // Front wall glass
    const wallGlassGeo1 = new THREE.PlaneGeometry(L, postH);
    const frontGlass = new THREE.Mesh(wallGlassGeo1, glassMat);
    frontGlass.position.set(L / 2, postY, 0);
    g.add(frontGlass);

    // Back wall glass
    const backGlass = new THREE.Mesh(wallGlassGeo1, glassMat);
    backGlass.position.set(L / 2, postY, W);
    g.add(backGlass);

    // Left wall glass
    const wallGlassGeo2 = new THREE.PlaneGeometry(W, postH);
    const leftGlass = new THREE.Mesh(wallGlassGeo2, glassMat);
    leftGlass.rotation.y = Math.PI / 2;
    leftGlass.position.set(0, postY, W / 2);
    g.add(leftGlass);

    // Right wall glass
    const rightGlass = new THREE.Mesh(wallGlassGeo2, glassMat);
    rightGlass.rotation.y = Math.PI / 2;
    rightGlass.position.set(L, postY, W / 2);
    g.add(rightGlass);

    // Roof glass
    const roofGlassGeo = new THREE.PlaneGeometry(L, W);
    const roofGlass = new THREE.Mesh(roofGlassGeo, glassMat);
    roofGlass.rotation.x = -Math.PI / 2;
    roofGlass.position.set(L / 2, H + 0.001, W / 2);
    g.add(roofGlass);

    // ---- Floor inside ----
    const floorGeo = new THREE.PlaneGeometry(L * 0.96, W * 0.96);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x4a3a28, roughness: 1 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(L / 2, 0.005, W / 2);
    floor.receiveShadow = true;
    g.add(floor);

    // ---- Plant beds ----
    this._buildPlants(L, W, baseH);

    // ---- Fan ----
    this._buildFan(L, W, H, baseH);

    // ---- LED ----
    this._buildLED(L, W, H);

    // ---- Sensors with labels ----
    this._buildSensors(L, W, H);

    // ---- Update orbit target ----
    this.target.set(L / 2, H * 0.45, W / 2);
    this.radius = Math.max(L, W, H) * 2.2;

    // Shadow camera
    const d = Math.max(L, W) * 2;
    this.sunLight.shadow.camera.left = -d;
    this.sunLight.shadow.camera.right = d;
    this.sunLight.shadow.camera.top = d;
    this.sunLight.shadow.camera.bottom = -d;
    this.sunLight.shadow.camera.near = 0.1;
    this.sunLight.shadow.camera.far = 40;
    this.sunLight.target.position.set(L / 2, 0, W / 2);
  }

  // ==================================================================
  _buildPlants(L, W, baseH) {
    const g = this.ghGroup;
    const bedMat = new THREE.MeshStandardMaterial({ color: 0x3d2815, roughness: 0.9 });
    const nBeds = Math.max(1, Math.round(W / 0.8));
    const bedW = (W * 0.7) / nBeds;
    const gap = (W * 0.3) / (nBeds + 1);

    for (let b = 0; b < nBeds; b++) {
      const bz = gap + b * (bedW + gap) + bedW / 2;
      const bedGeo = new THREE.BoxGeometry(L * 0.85, 0.08, bedW * 0.85);
      const bed = new THREE.Mesh(bedGeo, bedMat);
      bed.position.set(L / 2, 0.04, bz);
      bed.receiveShadow = true;
      g.add(bed);

      // Plants on beds
      const greens = [0x2d7a1e, 0x3a9b2a, 0x1e6c14, 0x4aab35, 0x287020];
      const nPlants = Math.max(3, Math.round(L / 0.25));
      for (let p = 0; p < nPlants; p++) {
        const px = L * 0.1 + (p / (nPlants - 1)) * L * 0.8;
        const pSize = 0.03 + Math.random() * 0.04;
        const plantGeo = new THREE.SphereGeometry(pSize, 8, 6);
        const plantMat = new THREE.MeshStandardMaterial({
          color: greens[Math.floor(Math.random() * greens.length)],
          roughness: 0.8
        });
        const plant = new THREE.Mesh(plantGeo, plantMat);
        plant.position.set(
          px + (Math.random() - 0.5) * 0.05,
          0.08 + pSize * 0.6,
          bz + (Math.random() - 0.5) * bedW * 0.5
        );
        plant.castShadow = true;
        g.add(plant);
      }
    }
  }

  // ==================================================================
  _buildFan(L, W, H, baseH) {
    const g = this.ghGroup;
    this.fanGroup = new THREE.Group();

    // Fan covers 25% of the wall it's mounted on (left wall = W × (H-baseH))
    const wallArea = W * (H - baseH);
    const fanSize = Math.sqrt(wallArea * 0.25);  // square fan side
    const fanDepth = fanSize * 0.3;

    // Housing
    const housingGeo = new THREE.BoxGeometry(fanDepth, fanSize, fanSize);
    const housingMat = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: 0.6, metalness: 0.3 });
    this.fanGroup.add(new THREE.Mesh(housingGeo, housingMat));

    // Guard ring
    const rimGeo = new THREE.TorusGeometry(fanSize * 0.38, fanSize * 0.025, 8, 24);
    const rimMat = new THREE.MeshStandardMaterial({ color: 0x2a2a2a, roughness: 0.5, metalness: 0.4 });
    const rim = new THREE.Mesh(rimGeo, rimMat);
    rim.rotation.y = Math.PI / 2;
    rim.position.x = -fanDepth / 2 - 0.003;
    this.fanGroup.add(rim);

    // Blades
    this.bladesGroup = new THREE.Group();
    this.bladesGroup.position.x = -fanDepth / 2 - 0.004;
    const bladeMat = new THREE.MeshStandardMaterial({
      color: 0x333333, roughness: 0.5, metalness: 0.2, side: THREE.DoubleSide
    });
    // Center hub
    const hubGeo = new THREE.CylinderGeometry(fanSize * 0.06, fanSize * 0.06, 0.012, 12);
    const hub = new THREE.Mesh(hubGeo, bladeMat);
    hub.rotation.z = Math.PI / 2;
    this.bladesGroup.add(hub);

    for (let i = 0; i < 4; i++) {
      const angle = (i / 4) * Math.PI * 2;
      const br = fanSize * 0.33;
      const shape = new THREE.Shape();
      shape.moveTo(0, 0);
      shape.quadraticCurveTo(br * 0.3, br * 0.15, br, br * 0.05);
      shape.lineTo(br, -br * 0.05);
      shape.quadraticCurveTo(br * 0.3, -br * 0.08, 0, 0);
      const bladeGeo = new THREE.ShapeGeometry(shape);
      const blade = new THREE.Mesh(bladeGeo, bladeMat);
      blade.rotation.x = angle;
      blade.rotation.y = Math.PI / 2;
      this.bladesGroup.add(blade);
    }
    this.fanGroup.add(this.bladesGroup);

    // Position on left wall (x=0), upper
    const fanY = baseH + (H - baseH) * 0.6;
    this.fanGroup.position.set(0.001, fanY, W / 2);
    g.add(this.fanGroup);

    // Fan label
    const fanLabel = makeLabel('🌀 Quạt thông gió', '#66ff66');
    fanLabel.position.set(0.001, fanY + fanSize * 0.7, W / 2);
    g.add(fanLabel);
  }

  // ==================================================================
  _buildLED(L, W, H) {
    const g = this.ghGroup;
    this.ledGroup = new THREE.Group();

    // LED strip bar under roof — spans 80% of length, wider and thicker
    const stripLen = L * 0.8;
    const stripW = W * 0.15;
    const stripGeo = new THREE.BoxGeometry(stripLen, 0.04, stripW);
    this.ledStrip = new THREE.Mesh(stripGeo, new THREE.MeshStandardMaterial({
      color: 0xcccccc, roughness: 0.3, metalness: 0.2
    }));
    this.ledGroup.add(this.ledStrip);

    // LED light source — stronger
    this.ledLight = new THREE.PointLight(0xfff5e0, 0, Math.max(L, W) * 3);
    this.ledLight.position.y = -0.05;
    this.ledGroup.add(this.ledLight);

    // Position centered under roof
    this.ledGroup.position.set(L / 2, H - 0.05, W / 2);
    g.add(this.ledGroup);

    // LED label
    const ledLabel = makeLabel('💡 Đèn LED', '#ffff66');
    ledLabel.position.set(L / 2, H - 0.15, W / 2);
    g.add(ledLabel);
  }

  // ==================================================================
  _buildSensors(L, W, H) {
    const g = this.ghGroup;

    // ---- SHT30 Sensor (temperature + humidity) ----
    // Gray cylinder, mounted on wall near roof
    const sht30Group = new THREE.Group();

    // Body
    const sht30Geo = new THREE.CylinderGeometry(0.025, 0.025, 0.03, 16);
    const sht30Mat = new THREE.MeshStandardMaterial({ color: 0x3a3a3a, roughness: 0.7, metalness: 0.2 });
    const sht30Body = new THREE.Mesh(sht30Geo, sht30Mat);
    sht30Body.rotation.x = Math.PI / 2;
    sht30Group.add(sht30Body);

    // Mesh grille
    const grilleGeo = new THREE.CylinderGeometry(0.022, 0.022, 0.005, 16);
    const grilleMat = new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.5, metalness: 0.3 });
    const grille = new THREE.Mesh(grilleGeo, grilleMat);
    grille.rotation.x = Math.PI / 2;
    grille.position.z = -0.018;
    sht30Group.add(grille);

    // Wire
    const wireMat = new THREE.MeshStandardMaterial({ color: 0xcc2222, roughness: 0.6, metalness: 0.1 });
    const wireGeo = new THREE.CylinderGeometry(0.004, 0.004, 0.12, 6);
    const wire = new THREE.Mesh(wireGeo, wireMat);
    wire.position.set(0, -0.06, 0.01);
    sht30Group.add(wire);

    // Position on back wall, upper right
    sht30Group.position.set(L * 0.7, H * 0.75, 0.04);
    g.add(sht30Group);

    // SHT30 label
    const sht30Label = makeLabel('🌡️ SHT30 (Nhiệt độ & Độ ẩm)', '#ff8888');
    sht30Label.position.set(L * 0.7, H * 0.75 + 0.12, 0.04);
    sht30Label.scale.set(0.7, 0.22, 1);
    g.add(sht30Label);

    // ---- Indicator dot for SHT30 ----
    const dotGeo = new THREE.SphereGeometry(0.015, 12, 8);
    const dotMat = new THREE.MeshBasicMaterial({ color: 0xff4444 });
    const sht30Dot = new THREE.Mesh(dotGeo, dotMat);
    sht30Dot.position.set(L * 0.7, H * 0.75 + 0.05, 0.04);
    g.add(sht30Dot);

    // ---- Light Sensor SEN0644 ----
    const lightSGroup = new THREE.Group();

    // White cylindrical body
    const lsGeo = new THREE.CylinderGeometry(0.01, 0.01, 0.05, 12);
    const lsMat = new THREE.MeshStandardMaterial({ color: 0xf0f0f0, roughness: 0.6, metalness: 0.1 });
    const lsBody = new THREE.Mesh(lsGeo, lsMat);
    lightSGroup.add(lsBody);

    // Brown sensing band
    const bandGeo = new THREE.CylinderGeometry(0.012, 0.012, 0.015, 12);
    const bandMat = new THREE.MeshStandardMaterial({ color: 0x8b7355, roughness: 0.8 });
    const band = new THREE.Mesh(bandGeo, bandMat);
    band.position.y = 0.008;
    lightSGroup.add(band);

    // White connector
    const capGeo = new THREE.CylinderGeometry(0.013, 0.013, 0.012, 8);
    const capMat = new THREE.MeshStandardMaterial({ color: 0xfafafa, roughness: 0.5 });
    const cap = new THREE.Mesh(capGeo, capMat);
    cap.position.y = -0.03;
    lightSGroup.add(cap);

    // Wire
    const lsWire = new THREE.Mesh(wireGeo.clone(), wireMat);
    lsWire.position.set(0, -0.09, 0);
    lightSGroup.add(lsWire);

    // Position on right wall, upper area
    lightSGroup.position.set(L - 0.04, H * 0.65, W * 0.6);
    g.add(lightSGroup);

    // Light sensor label
    const lsLabel = makeLabel('☀️ SEN0644 (Ánh sáng)', '#ffcc44');
    lsLabel.position.set(L - 0.04, H * 0.65 + 0.15, W * 0.6);
    lsLabel.scale.set(0.6, 0.2, 1);
    g.add(lsLabel);

    // Indicator dot
    const lsDot = new THREE.Mesh(dotGeo.clone(), new THREE.MeshBasicMaterial({ color: 0xffaa00 }));
    lsDot.position.set(L - 0.04, H * 0.65 + 0.07, W * 0.6);
    g.add(lsDot);

    // ---- Relay module (blue box on ground near wall) ----
    const relayGeo = new THREE.BoxGeometry(0.06, 0.04, 0.03);
    const relayMat = new THREE.MeshStandardMaterial({ color: 0x2244aa, roughness: 0.5, metalness: 0.1 });
    const relay = new THREE.Mesh(relayGeo, relayMat);
    relay.position.set(L * 0.3, 0.02, 0.04);
    g.add(relay);

    const relayLabel = makeLabel('🔗 Relay 2 kênh', '#88aaff');
    relayLabel.position.set(L * 0.3, 0.12, 0.04);
    relayLabel.scale.set(0.5, 0.16, 1);
    g.add(relayLabel);

    // ---- RS485 converter (small blue USB module on ground) ----
    const rs485Geo = new THREE.BoxGeometry(0.04, 0.015, 0.02);
    const rs485Mat = new THREE.MeshStandardMaterial({ color: 0x3366cc, roughness: 0.4, metalness: 0.2 });
    const rs485 = new THREE.Mesh(rs485Geo, rs485Mat);
    rs485.position.set(L * 0.3 + 0.08, 0.01, 0.04);
    g.add(rs485);
  }

  // ==================================================================
  // Clouds — fluffy white shapes in the sky
  // ==================================================================
  _buildClouds() {
    const cloudMat = new THREE.MeshStandardMaterial({
      color: 0xffffff, roughness: 1, metalness: 0,
      transparent: true, opacity: 0.85,
    });
    // Create 8 cloud clusters at various positions
    for (let i = 0; i < 8; i++) {
      const cg = new THREE.Group();
      // Each cloud = cluster of 3-5 stretched spheres
      const nBlobs = 3 + Math.floor(Math.random() * 3);
      for (let b = 0; b < nBlobs; b++) {
        const sx = 0.4 + Math.random() * 0.6;
        const sy = 0.15 + Math.random() * 0.15;
        const sz = 0.3 + Math.random() * 0.4;
        const geo = new THREE.SphereGeometry(1, 8, 6);
        const mesh = new THREE.Mesh(geo, cloudMat);
        mesh.scale.set(sx, sy, sz);
        mesh.position.set(
          (Math.random() - 0.5) * 0.8,
          (Math.random() - 0.5) * 0.1,
          (Math.random() - 0.5) * 0.5
        );
        cg.add(mesh);
      }
      // Spread clouds across the sky
      const L = this.model.length, W = this.model.width;
      cg.position.set(
        L / 2 + (Math.random() - 0.5) * 12,
        5 + Math.random() * 3,
        W / 2 + (Math.random() - 0.5) * 12
      );
      cg.userData.driftX = (Math.random() - 0.5) * 0.003;
      cg.userData.baseX = cg.position.x;
      this.scene.add(cg);
      this.clouds.push(cg);
    }
  }

  // ==================================================================
  // Camera orbit controls
  // ==================================================================
  _setupControls() {
    let isDrag = false, px = 0, py = 0, pinchD = 0;
    const touches = new Map();

    const onDown = e => {
      isDrag = true; px = e.clientX; py = e.clientY;
      this.canvas.setPointerCapture(e.pointerId);
    };
    const onMove = e => {
      if (!isDrag) return;
      this.theta -= (e.clientX - px) * 0.008;
      this.phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.05,
        this.phi - (e.clientY - py) * 0.008));
      px = e.clientX; py = e.clientY;
    };
    const onUp = () => { isDrag = false; };
    const onWheel = e => {
      this.radius = Math.max(0.8, Math.min(20,
        this.radius + e.deltaY * 0.005));
      e.preventDefault();
    };
    const onTS = e => {
      for (const t of e.changedTouches) touches.set(t.identifier, t);
      if (touches.size === 2) {
        const [a, b] = [...touches.values()];
        pinchD = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      }
    };
    const onTM = e => {
      for (const t of e.changedTouches) touches.set(t.identifier, t);
      if (touches.size === 2) {
        const [a, b] = [...touches.values()];
        const d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        this.radius = Math.max(0.8, Math.min(20, this.radius * (pinchD / Math.max(d, 1))));
        pinchD = d;
      }
    };
    const onTE = e => { for (const t of e.changedTouches) touches.delete(t.identifier); };

    this.canvas.addEventListener('pointerdown', onDown);
    this.canvas.addEventListener('pointermove', onMove);
    this.canvas.addEventListener('pointerup', onUp);
    this.canvas.addEventListener('pointercancel', onUp);
    this.canvas.addEventListener('wheel', onWheel, { passive: false });
    this.canvas.addEventListener('touchstart', onTS, { passive: true });
    this.canvas.addEventListener('touchmove', onTM, { passive: true });
    this.canvas.addEventListener('touchend', onTE);

    this._cleanupCtrl = () => {
      this.canvas.removeEventListener('pointerdown', onDown);
      this.canvas.removeEventListener('pointermove', onMove);
      this.canvas.removeEventListener('pointerup', onUp);
      this.canvas.removeEventListener('pointercancel', onUp);
      this.canvas.removeEventListener('wheel', onWheel);
      this.canvas.removeEventListener('touchstart', onTS);
      this.canvas.removeEventListener('touchmove', onTM);
      this.canvas.removeEventListener('touchend', onTE);
    };
  }

  _updateCamera() {
    const t = this.target;
    this.camera.position.set(
      t.x + this.radius * Math.sin(this.phi) * Math.sin(this.theta),
      t.y + this.radius * Math.cos(this.phi),
      t.z + this.radius * Math.sin(this.phi) * Math.cos(this.theta)
    );
    this.camera.lookAt(t);
  }

  _handleResize() {
    const box = this.canvas.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) return;
    const w = Math.round(box.width), h = Math.round(box.height);
    const pr = this.renderer.getPixelRatio();
    if (this.canvas.width !== w * pr || this.canvas.height !== h * pr) {
      this.renderer.setSize(w, h, false);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
    }
  }

  // ==================================================================
  // Update (per frame)
  // ==================================================================
  update() {
    if (this._disposed) return;

    const hour = this.model.simHour;

    // Fan blades
    if (this.model.fanOn && this.bladesGroup) {
      this.bladesGroup.rotation.x += 0.25;
    }

    // LED
    if (this.ledStrip) {
      if (this.model.ledOn) {
        this.ledStrip.material.emissive.setHex(0xffffcc);
        this.ledStrip.material.emissiveIntensity = 2.0;
        this.ledLight.intensity = 5.0;
      } else {
        this.ledStrip.material.emissive.setHex(0x000000);
        this.ledStrip.material.emissiveIntensity = 0;
        this.ledLight.intensity = 0;
      }
    }

    // Sun
    const sunAngle = ((hour - 6) / 12) * Math.PI;
    const sunUp = hour >= 5.5 && hour <= 18.5;
    this.sun.visible = sunUp;
    const L = this.model.length, W = this.model.width;

    if (sunUp) {
      const sr = 8;
      this.sun.position.set(
        L / 2 + sr * Math.cos(sunAngle) * 0.3,
        Math.max(0.5, sr * Math.sin(sunAngle)),
        W / 2 - sr * Math.cos(sunAngle)
      );
      this.sunLight.position.copy(this.sun.position);
      const elev = Math.sin(sunAngle);
      const warm = 1 - elev;
      this.sun.material.color.setHSL(0.1 * warm, 0.9, 0.5 + 0.3 * elev);
      this.sunLight.color.setHSL(0.08 * warm, 0.6, 0.6 + 0.2 * elev);
      this.sunLight.intensity = 0.5 + 1.5 * elev * (1 - this.model.cloudCover * 0.6);
    } else {
      this.sunLight.intensity = 0;
    }

    // Sky
    if (hour < 5 || hour > 19.5) {
      this.scene.background.setHex(0x0a1628);
      this.ambientLight.intensity = 0.08;
      this.hemiLight.intensity = 0.05;
    } else if (hour < 6.5 || hour > 18) {
      const t = hour < 12 ? (hour - 5) / 1.5 : (19.5 - hour) / 1.5;
      this.scene.background.setHSL(0.55, 0.4, 0.15 + 0.4 * t);
      this.ambientLight.intensity = 0.1 + 0.25 * t;
      this.hemiLight.intensity = 0.1 + 0.2 * t;
    } else {
      const c = this.model.cloudCover;
      this.scene.background.setHSL(0.55, 0.55 - 0.3 * c, 0.65 - 0.15 * c);
      this.ambientLight.intensity = 0.3 + 0.15 * (1 - c);
      this.hemiLight.intensity = 0.25 + 0.15 * (1 - c);
    }

    // Clouds — visibility based on cloudCover, slow drift
    const cc = this.model.cloudCover;
    for (let i = 0; i < this.clouds.length; i++) {
      const cg = this.clouds[i];
      // Show more clouds as cloudCover increases
      const threshold = (i + 1) / this.clouds.length;
      cg.visible = cc >= threshold * 0.9 && (hour >= 5 && hour <= 19.5);
      // Drift sideways
      cg.position.x = cg.userData.baseX + Math.sin(Date.now() * 0.0001 + i) * 1.5;
      // Opacity scales with cloud cover
      cg.traverse(obj => {
        if (obj.material && obj.material.opacity !== undefined) {
          obj.material.opacity = 0.5 + cc * 0.4;
        }
      });
    }

    this._updateCamera();
    this._handleResize();
    this.renderer.render(this.scene, this.camera);
  }

  // ==================================================================
  dispose() {
    this._disposed = true;
    if (this._cleanupCtrl) this._cleanupCtrl();
    this.renderer.dispose();
    this.clouds = [];
    this.scene.traverse(obj => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
        else obj.material.dispose();
      }
    });
  }
}
