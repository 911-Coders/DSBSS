
        // Inject Python CP-SAT / Timetable Data
        let RAW_DATA = `__INJECTED_DATA__`;
        let SERVER_DATA = { trajectories: [], solver_start: 0, solver_end: 0 };
        try { if(!RAW_DATA.includes("__INJECTED")) SERVER_DATA = JSON.parse(RAW_DATA); } catch(e) { console.error(e); }

        const CONFIG = {
            gridSize: 30,
            simSpeed: 1, // Timeline playback speed
            isPaused: false,
            colors: {
                bgDark: '#0f172a', bgLight: '#1e293b',
                track: '#94a3b8', trackGlow: '#38bdf8', tie: '#334155', trackMaint: '#ca8a04',
                trainPre: '#ef4444', trainExp: '#f59e0b', trainFrt: '#3b82f6',
                sigG: '#22c55e', sigY: '#eab308', sigR: '#ef4444'
            }
        };

        const state = {
            time: 0, // Minutes
            camera: { x: 0, y: 0, zoom: 0.8 },
            tool: 'select',
            hoveredGrid: { x: 0, y: 0 },
            dragStart: null,
            selectedTrainId: null,
            weather: false,
            particles: [],
            isMaintenance: false,
            nodes: new Map(),
            edges: new Map(),
            stations: [],
            signals: [],
            blocks: [],
            trainDefs: [], // Base definitions
            trainStates: new Map() // Playback history mapping: TrainId -> array of states
        };

        const canvas = document.getElementById('sim-canvas');
        const ctx = canvas.getContext('2d');
        const toastEl = document.getElementById('toast');
        const scrubber = document.getElementById('time-scrubber');
        const clockDisplay = document.getElementById('clock-display');
        const loader = document.getElementById('loading-overlay');
        
        const sStart = SERVER_DATA.solver_start || 0;
        const sEnd = SERVER_DATA.solver_end || 0;
        if(sEnd > sStart) {
            const hL = document.getElementById('shadow-block-highlight');
            hL.style.left = (sStart / 1440 * 100) + '%';
            hL.style.width = ((sEnd - sStart) / 1440 * 100) + '%';
        }

        function showToast(msg) { toastEl.innerText = msg; toastEl.style.opacity = 1; setTimeout(() => toastEl.style.opacity = 0, 2000); }
        function formatTime(mins) { let h = Math.floor(mins / 60); let m = Math.floor(mins % 60); return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`; }

        // --- GRAPH LOGIC ---
        function resize() { canvas.width = canvas.parentElement.clientWidth; canvas.height = canvas.parentElement.clientHeight; }
        window.addEventListener('resize', resize); resize();
        function getMousePos(evt) { const rect = canvas.getBoundingClientRect(); return { x: evt.clientX - rect.left, y: evt.clientY - rect.top }; }
        function screenToWorld(x, y) { return { x: (x - state.camera.x) / state.camera.zoom, y: (y - state.camera.y) / state.camera.zoom }; }
        function worldToGrid(x, y) { return { x: Math.round(x / CONFIG.gridSize), y: Math.round(y / CONFIG.gridSize) }; }
        function getId(x, y) { return `${x},${y}`; }
        function addNode(x, y) { let id = getId(x, y); if (!state.nodes.has(id)) state.nodes.set(id, { id, x, y, edges: [] }); return id; }
        function addEdge(n1_id, n2_id, type="main") {
            if(n1_id === n2_id) return null;
            let id = `${n1_id}_${n2_id}`, idRev = `${n2_id}_${n1_id}`;
            if (state.edges.has(id) || state.edges.has(idRev)) return null;
            let n1 = state.nodes.get(n1_id), n2 = state.nodes.get(n2_id);
            let length = Math.sqrt(Math.pow(n2.x - n1.x, 2) + Math.pow(n2.y - n1.y, 2));
            let edge = { id, n1: n1_id, n2: n2_id, length, broken: false, type: type };
            state.edges.set(id, edge); n1.edges.push(id); n2.edges.push(id);
            return edge;
        }
        function removeEdge(id) {
            if(!state.edges.has(id)) return;
            let edge = state.edges.get(id);
            state.nodes.get(edge.n1).edges = state.nodes.get(edge.n1).edges.filter(e => e !== id);
            state.nodes.get(edge.n2).edges = state.nodes.get(edge.n2).edges.filter(e => e !== id);
            state.signals = state.signals.filter(s => s.edgeId !== id);
            state.edges.delete(id); recalculateBlocks(); runHeadlessSimulation();
        }
        function getEdgeAt(worldX, worldY) {
            const gx = worldX / CONFIG.gridSize, gy = worldY / CONFIG.gridSize;
            let best = null, minDist = Infinity;
            for (let [id, edge] of state.edges) {
                let n1 = state.nodes.get(edge.n1), n2 = state.nodes.get(edge.n2);
                let d = distToSegment({x:gx, y:gy}, n1, n2);
                if (d < 0.4 && d < minDist) { minDist = d; best = edge; }
            }
            return best;
        }
        function distToSegment(p, v, w) {
            let l2 = Math.pow(w.x - v.x, 2) + Math.pow(w.y - v.y, 2);
            if (l2 === 0) return Math.sqrt(Math.pow(p.x - v.x, 2) + Math.pow(p.y - v.y, 2));
            let t = ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2;
            t = Math.max(0, Math.min(1, t));
            return Math.sqrt(Math.pow(p.x - (v.x + t * (w.x - v.x)), 2) + Math.pow(p.y - (v.y + t * (w.y - v.y)), 2));
        }

        function recalculateBlocks() {
            state.blocks = []; let visitedEdges = new Set();
            let edgeSignals = new Map();
            for(let s of state.signals) { if(!edgeSignals.has(s.edgeId)) edgeSignals.set(s.edgeId, []); edgeSignals.get(s.edgeId).push(s); }
            for (let [edgeId, edge] of state.edges) {
                if (visitedEdges.has(edgeId)) continue;
                let currentBlock = { id: state.blocks.length, edges: new Set() };
                let queue = [edgeId];
                while(queue.length > 0) {
                    let currId = queue.shift();
                    if(visitedEdges.has(currId)) continue;
                    visitedEdges.add(currId); currentBlock.edges.add(currId);
                    let cEdge = state.edges.get(currId);
                    for (let node of [state.nodes.get(cEdge.n1), state.nodes.get(cEdge.n2)]) {
                        for (let nextEdgeId of node.edges) {
                            if (nextEdgeId === currId || visitedEdges.has(nextEdgeId)) continue;
                            if (!edgeSignals.has(currId) && !edgeSignals.has(nextEdgeId)) queue.push(nextEdgeId);
                        }
                    }
                }
                state.blocks.push(currentBlock);
            }
        }
        function getBlockForEdge(edgeId) { return state.blocks.find(b => b.edges.has(edgeId)); }

        // --- PATHFINDING ---
        // Intelligent pathfinding that routes Express to Main and Freight to Loops
        function getNextEdge(trainState, currEdge, forwardNodeId, trainDef) {
            let node = state.nodes.get(forwardNodeId);
            let choices = node.edges.filter(eid => eid !== currEdge.id);
            if(choices.length === 0) return null;
            if(choices.length === 1) return choices[0];

            let isFreight = trainDef.type.includes('Freight');
            
            choices.sort((a, b) => {
                let eA = state.edges.get(a), eB = state.edges.get(b);
                let scoreA = 0, scoreB = 0;
                
                // Prioritize going "straight" relative to direction
                let tA = eA.n1 === forwardNodeId ? state.nodes.get(eA.n2) : state.nodes.get(eA.n1);
                let tB = eB.n1 === forwardNodeId ? state.nodes.get(eB.n2) : state.nodes.get(eB.n1);
                
                // Prefer same X coordinate to avoid unnecessary lane changes
                if(tA.x === node.x) scoreA += 5;
                if(tB.x === node.x) scoreB += 5;
                
                // Freight prefers loops (x=5 or x=20), Express prefers main (x=10 or x=15)
                let aIsLoop = (tA.x === 5 || tA.x === 20);
                let bIsLoop = (tB.x === 5 || tB.x === 20);
                
                if(isFreight) {
                    if(aIsLoop) scoreA += 10;
                    if(bIsLoop) scoreB += 10;
                } else {
                    if(!aIsLoop) scoreA += 10;
                    if(!bIsLoop) scoreB += 10;
                }
                
                // Keep moving in original y-direction (UP=-y, DOWN=+y)
                let dirY = trainState.direction; 
                let dyA = tA.y - node.y; let dyB = tB.y - node.y;
                if (dyA > 0 && dirY === 1) scoreA += 20; if (dyA < 0 && dirY === -1) scoreA += 20;
                if (dyB > 0 && dirY === 1) scoreB += 20; if (dyB < 0 && dirY === -1) scoreB += 20;

                return scoreB - scoreA; // highest score first
            });
            
            return choices[0];
        }

        // --- HEADLESS PRE-COMPUTATION ENGINE ---
        // Runs instantly and calculates the history array for every train
        function runHeadlessSimulation() {
            loader.style.display = 'flex';
            setTimeout(() => {
                state.trainStates = new Map();
                let blocksState = new Map(); // blockId -> occupiedByTrainId
                let signalState = new Map(); // signalIdx -> state
                
                // Initialize trains
                let activeTrains = [];
                for(let tDef of state.trainDefs) {
                    activeTrains.push({
                        def: tDef,
                        path: [tDef.startEdgeId], pathIdx: 0, progress: 0.1,
                        speed: 0, direction: tDef.startDir, nextSig: 'G', active: false,
                        history: []
                    });
                }

                // Simulate 24 hours at 0.5 minute steps
                for(let t = 0; t <= 1440; t += 0.5) {
                    // Clear blocks
                    blocksState.clear();
                    
                    let isMaintWindow = (t >= sStart && t <= sEnd && sEnd > sStart);
                    
                    // Register block occupancy
                    for(let tr of activeTrains) {
                        if(tr.active) {
                            let b = getBlockForEdge(tr.path[tr.pathIdx]);
                            if(b) blocksState.set(b.id, tr.def.id);
                        }
                    }

                    for(let tr of activeTrains) {
                        // Spawn check
                        if(!tr.active && t >= tr.def.entry_min) { tr.active = true; }
                        if(!tr.active) { tr.history.push(null); continue; }
                        
                        let currEdge = state.edges.get(tr.path[tr.pathIdx]);
                        if(!currEdge) { tr.active = false; tr.history.push(null); continue; }
                        
                        let myBlock = getBlockForEdge(currEdge.id);
                        let targetSpeed = tr.def.speedMax;
                        if(state.weather) targetSpeed *= 0.5;
                        if(currEdge.broken || isMaintWindow) targetSpeed = 0; // Stop for fault/maint

                        tr.nextSig = 'G';
                        let forwardNodeId = tr.direction === 1 ? currEdge.n2 : currEdge.n1;
                        let lookAheadEdgeId = tr.pathIdx < tr.path.length - 1 ? tr.path[tr.pathIdx+1] : getNextEdge(tr, currEdge, forwardNodeId, tr.def);
                        
                        if (lookAheadEdgeId) {
                            let nextBlock = getBlockForEdge(lookAheadEdgeId);
                            let nextEdge = state.edges.get(lookAheadEdgeId);
                            
                            // Check collision
                            if (nextBlock && nextBlock !== myBlock && blocksState.has(nextBlock.id) && blocksState.get(nextBlock.id) !== tr.def.id) {
                                tr.nextSig = 'R';
                                targetSpeed = tr.progress > 0.8 ? 0 : targetSpeed * 0.4;
                            }
                            if (nextEdge.broken && tr.progress > 0.7) targetSpeed = 0;
                        } else if (tr.progress > 0.8) targetSpeed = 0;

                        // Physics
                        if (tr.speed < targetSpeed) tr.speed += 5.0; // Fast accel
                        if (tr.speed > targetSpeed) tr.speed -= 10.0;
                        if (tr.speed < 0) tr.speed = 0;
                        if (targetSpeed === 0 && tr.speed < 10) tr.speed = 0;

                        if (tr.speed > 0) {
                            let dt_sec = 0.5 * 60; // 30 seconds per step
                            let moveDist = (tr.speed / 3600) * dt_sec * 30; // scaled down distance
                            tr.progress += moveDist / currEdge.length;
                            
                            if(tr.progress >= 1) {
                                if (lookAheadEdgeId) {
                                    let nextE = state.edges.get(lookAheadEdgeId);
                                    let fnId = tr.direction === 1 ? currEdge.n2 : currEdge.n1;
                                    tr.direction = nextE.n1 === fnId ? 1 : -1;
                                    tr.path.push(lookAheadEdgeId); tr.pathIdx++; tr.progress = 0;
                                } else tr.progress = 1;
                            }
                        }
                        
                        // Save geometry state
                        currEdge = state.edges.get(tr.path[tr.pathIdx]);
                        let startNode = tr.direction === 1 ? state.nodes.get(currEdge.n1) : state.nodes.get(currEdge.n2);
                        let endNode = tr.direction === 1 ? state.nodes.get(currEdge.n2) : state.nodes.get(currEdge.n1);
                        let hx = startNode.x + (endNode.x - startNode.x) * tr.progress;
                        let hy = startNode.y + (endNode.y - startNode.y) * tr.progress;
                        let angle = Math.atan2(endNode.y - startNode.y, endNode.x - startNode.x);
                        
                        tr.history.push({ x: hx, y: hy, angle: angle, speed: tr.speed, sig: tr.nextSig });
                    }
                }
                
                // Commit to state
                for(let tr of activeTrains) state.trainStates.set(tr.def.id, tr.history);
                loader.style.display = 'none';
            }, 50);
        }

        // --- COMPLEX TRACK LAYOUT ---
        function initComplexLayout() {
            // Complex 4-Track Mainline from y=0 to y=60
            const L_LOOP = 5, L_MAIN = 10, R_MAIN = 15, R_LOOP = 20;
            
            for(let y=0; y<60; y+=5) {
                addEdge(addNode(L_LOOP, y), addNode(L_LOOP, y+5));
                addEdge(addNode(L_MAIN, y), addNode(L_MAIN, y+5));
                addEdge(addNode(R_MAIN, y), addNode(R_MAIN, y+5));
                addEdge(addNode(R_LOOP, y), addNode(R_LOOP, y+5));
            }

            const createDiamond = (y) => {
                // Diamond Crossover
                addEdge(addNode(L_MAIN, y), addNode(L_LOOP, y+5));
                addEdge(addNode(L_LOOP, y), addNode(L_MAIN, y+5));
                addEdge(addNode(R_MAIN, y), addNode(R_LOOP, y+5));
                addEdge(addNode(R_LOOP, y), addNode(R_MAIN, y+5));
                addEdge(addNode(L_MAIN, y), addNode(R_MAIN, y+5));
                addEdge(addNode(R_MAIN, y), addNode(L_MAIN, y+5));
                
                // Signals at crossover
                state.signals.push({ edgeId: `${L_MAIN},${y}_${L_MAIN},${y+5}`, pos: 0.1, state: 'G' });
                state.signals.push({ edgeId: `${R_MAIN},${y}_${R_MAIN},${y+5}`, pos: 0.1, state: 'G' });
                state.signals.push({ edgeId: `${L_LOOP},${y}_${L_LOOP},${y+5}`, pos: 0.1, state: 'G' });
                state.signals.push({ edgeId: `${R_LOOP},${y}_${R_LOOP},${y+5}`, pos: 0.1, state: 'G' });
            }

            createDiamond(10); // PERN throat
            createDiamond(25); // THVM throat
            createDiamond(40); // KRMI throat
            createDiamond(55); // MAO throat

            state.stations.push({ name: 'PERN', x: 12.5, y: 5, w: 20, h: 4 });
            state.stations.push({ name: 'THVM', x: 12.5, y: 20, w: 20, h: 4 });
            state.stations.push({ name: 'KRMI', x: 12.5, y: 35, w: 20, h: 4 });
            state.stations.push({ name: 'MAO',  x: 12.5, y: 50, w: 20, h: 4 });

            recalculateBlocks();
            
            // Load Schedule Trains
            for(let t of SERVER_DATA.trajectories) {
                let isUp = t.direction.includes('UP');
                let startEdge = isUp ? `10,55_10,50` : `15,0_15,5`; // L_MAIN for UP, R_MAIN for DOWN
                if(t.category.includes('Freight')) startEdge = isUp ? `5,55_5,50` : `20,0_20,5`; // Loops for Freight
                
                state.trainDefs.push({
                    id: t.train_no, name: t.train_name, type: t.category,
                    startEdgeId: startEdge, startDir: isUp ? -1 : 1,
                    entry_min: t.entry_min, speedMax: t.category.includes('Premium') ? 140 : t.category.includes('Express') ? 100 : 60
                });
            }

            state.camera.x = canvas.width/2 - 12.5 * CONFIG.gridSize;
            state.camera.y = 50;

            runHeadlessSimulation(); // Pre-compute entire day instantly
        }

        // --- INPUTS ---
        let isPanning = false;
        canvas.addEventListener('mousedown', (e) => {
            if (e.button === 1 || e.button === 2 || (e.button === 0 && state.tool === 'select')) { isPanning = true; document.getElementById('canvas-container').classList.add('panning'); return; }
            if (e.button !== 0) return;
            
            const wPos = screenToWorld(getMousePos(e).x, getMousePos(e).y);
            const grid = worldToGrid(wPos.x, wPos.y);
            
            if (state.tool === 'track') state.dragStart = { ...grid };
            else if (state.tool === 'delete') { let edge = getEdgeAt(wPos.x, wPos.y); if(edge) { removeEdge(edge.id); showToast("Deleted"); } }
            else if (state.tool === 'break_rail') { 
                let edge = getEdgeAt(wPos.x, wPos.y); 
                if(edge) { edge.broken = !edge.broken; showToast(edge.broken ? "Rail Broken" : "Repaired"); runHeadlessSimulation(); } 
            }
            else if (state.tool === 'train') { 
                let edge = getEdgeAt(wPos.x, wPos.y); 
                if(edge) { 
                    state.trainDefs.push({ id: 'TR-' + Date.now(), name: 'Custom Train', type: 'Express', startEdgeId: edge.id, startDir: 1, entry_min: state.time, speedMax: 100 });
                    showToast("Train Scheduled"); runHeadlessSimulation();
                } 
            }
        });
        
        canvas.addEventListener('mousemove', (e) => {
            if (isPanning) { state.camera.x += e.movementX; state.camera.y += e.movementY; }
            const wPos = screenToWorld(getMousePos(e).x, getMousePos(e).y);
            state.hoveredGrid = worldToGrid(wPos.x, wPos.y);
        });
        
        canvas.addEventListener('mouseup', (e) => {
            isPanning = false; document.getElementById('canvas-container').classList.remove('panning');
            if (e.button === 0 && state.tool === 'select' && !isPanning) {
                const wPos = screenToWorld(getMousePos(e).x, getMousePos(e).y);
                state.selectedTrainId = null;
                // Hit test using interpolated positions
                let stepIdx = Math.floor(state.time * 2);
                for (let [tId, hist] of state.trainStates) {
                    let h = hist[stepIdx]; if(!h) continue;
                    if(Math.abs(wPos.x - h.x*CONFIG.gridSize) < 20 && Math.abs(wPos.y - h.y*CONFIG.gridSize) < 20) { state.selectedTrainId = tId; break; }
                }
                updateInfoPanel();
            }
            if (e.button === 0 && state.tool === 'track' && state.dragStart) {
                if (state.dragStart.x !== state.hoveredGrid.x || state.dragStart.y !== state.hoveredGrid.y) {
                    addEdge(addNode(state.dragStart.x, state.dragStart.y), addNode(state.hoveredGrid.x, state.hoveredGrid.y));
                    recalculateBlocks(); runHeadlessSimulation();
                }
                state.dragStart = null;
            }
        });

        canvas.addEventListener('contextmenu', e => e.preventDefault());
        canvas.addEventListener('wheel', (e) => {
            e.preventDefault(); const mPos = getMousePos(e); const z = -e.deltaY * 0.001; const newZ = Math.max(0.2, Math.min(4, state.camera.zoom + z));
            state.camera.x = mPos.x - (mPos.x - state.camera.x) * (newZ / state.camera.zoom); state.camera.y = mPos.y - (mPos.y - state.camera.y) * (newZ / state.camera.zoom); state.camera.zoom = newZ;
        });

        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', () => { document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active'); state.tool = btn.dataset.tool; document.getElementById('canvas-container').className = (state.tool !== 'select' && state.tool !== 'delete') ? 'tool-active' : ''; });
        });
        document.querySelectorAll('.speed-btn').forEach(btn => { btn.addEventListener('click', () => { document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active'); CONFIG.simSpeed = parseFloat(btn.dataset.speed); }); });
        document.getElementById('btn-play').addEventListener('click', (e) => { state.isPaused = false; e.currentTarget.classList.add('active'); document.getElementById('btn-pause').classList.remove('active'); });
        document.getElementById('btn-pause').addEventListener('click', (e) => { state.isPaused = true; e.currentTarget.classList.add('active'); document.getElementById('btn-play').classList.remove('active'); });
        document.getElementById('btn-fullscreen').addEventListener('click', () => { if (!document.fullscreenElement) document.documentElement.requestFullscreen(); else if (document.exitFullscreen) document.exitFullscreen(); });
        
        scrubber.addEventListener('input', (e) => { state.time = parseFloat(e.target.value); clockDisplay.innerText = formatTime(state.time); if(state.selectedTrainId) updateInfoPanel(); });

        document.getElementById('disrupt-weather').addEventListener('click', (e) => {
            state.weather = !state.weather; e.currentTarget.classList.toggle('active', state.weather);
            if(state.weather) { state.particles = []; for(let i=0; i<300; i++) state.particles.push({x: Math.random()*canvas.width, y: Math.random()*canvas.height, s: Math.random()*5+5}); }
            runHeadlessSimulation(); // Recalculate speeds
        });
        document.getElementById('btn-clear-faults').addEventListener('click', () => { 
            state.weather = false; document.getElementById('disrupt-weather').classList.remove('active'); 
            for(let [id, e] of state.edges) e.broken = false; 
            showToast("Repaired"); runHeadlessSimulation(); 
        });

        function updateInfoPanel() {
            const p = document.getElementById('info-panel');
            if(!state.selectedTrainId) { p.style.display = 'none'; return; }
            
            let tDef = state.trainDefs.find(d => d.id === state.selectedTrainId);
            let hist = state.trainStates.get(state.selectedTrainId);
            let h = hist[Math.floor(state.time * 2)]; // 0.5 step index
            if(!h) { p.style.display = 'none'; return; }

            p.style.display = 'block';
            document.getElementById('info-title').firstElementChild.innerText = tDef.name;
            document.getElementById('info-type').innerText = tDef.type;
            let color = tDef.type.includes('Premium') ? CONFIG.colors.trainPre : tDef.type.includes('Express') ? CONFIG.colors.trainExp : CONFIG.colors.trainFrt;
            document.getElementById('info-type').style.color = color;
            let spd = Math.round(h.speed); document.getElementById('info-speed').innerText = spd + " km/h";
            let badge = document.getElementById('info-badge');
            if(spd === 0) { badge.className = 'status-badge status-stopped'; badge.innerText = 'STOPPED'; } else { badge.className = 'status-badge status-moving'; badge.innerText = 'MOVING'; }
            let sigEl = document.getElementById('info-signal');
            sigEl.innerText = h.sig === 'G' ? 'Clear' : h.sig === 'R' ? 'Danger' : 'Caution'; sigEl.style.color = h.sig === 'G' ? CONFIG.colors.sigG : CONFIG.colors.sigR;
        }

        // --- PLAYBACK RENDER LOOP ---
        let lastTime = performance.now();
        function loop(realTime) {
            let dt = (realTime - lastTime) / 1000;
            lastTime = realTime;
            
            if(!state.isPaused) {
                state.time += dt * (CONFIG.simSpeed / 60) * 10;
                if(state.time > 1440) state.time = 0;
                scrubber.value = state.time; clockDisplay.innerText = formatTime(state.time);
                if(state.selectedTrainId && realTime % 200 < 20) updateInfoPanel();
            }

            state.isMaintenance = (state.time >= sStart && state.time <= sEnd && sEnd > sStart);
            document.getElementById('maintenance-alert').classList.toggle('active', state.isMaintenance);

            ctx.fillStyle = CONFIG.colors.bgDark; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.save(); ctx.translate(state.camera.x, state.camera.y); ctx.scale(state.camera.zoom, state.camera.zoom);
            const gs = CONFIG.gridSize;
            
            // Edges
            for (let [id, edge] of state.edges) {
                let n1 = state.nodes.get(edge.n1), n2 = state.nodes.get(edge.n2);
                let isHovered = (state.tool === 'delete' || state.tool === 'break_rail') && getEdgeAt(state.hoveredGrid.x * gs, state.hoveredGrid.y * gs) === edge;
                
                if (isHovered) {
                    ctx.strokeStyle = edge.broken ? '#ef4444' : CONFIG.colors.trackGlow; ctx.globalAlpha = 0.4; ctx.lineWidth = 18;
                    ctx.beginPath(); ctx.moveTo(n1.x*gs, n1.y*gs); ctx.lineTo(n2.x*gs, n2.y*gs); ctx.stroke(); ctx.globalAlpha = 1.0;
                }
                
                if (state.isMaintenance) { ctx.strokeStyle = 'rgba(234, 179, 8, 0.4)'; ctx.lineWidth = 14; ctx.beginPath(); ctx.moveTo(n1.x*gs, n1.y*gs); ctx.lineTo(n2.x*gs, n2.y*gs); ctx.stroke(); }
                if (edge.broken) { ctx.strokeStyle = 'rgba(239, 68, 68, 0.6)'; ctx.lineWidth = 14; ctx.beginPath(); ctx.moveTo(n1.x*gs, n1.y*gs); ctx.lineTo(n2.x*gs, n2.y*gs); ctx.stroke(); }

                ctx.strokeStyle = CONFIG.colors.tie; ctx.setLineDash([3, 7]); ctx.lineWidth = 10; ctx.beginPath(); ctx.moveTo(n1.x*gs, n1.y*gs); ctx.lineTo(n2.x*gs, n2.y*gs); ctx.stroke();
                ctx.strokeStyle = state.isMaintenance ? CONFIG.colors.trackMaint : CONFIG.colors.track; ctx.setLineDash([]); ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(n1.x*gs, n1.y*gs); ctx.lineTo(n2.x*gs, n2.y*gs); ctx.stroke();
            }

            // Signals
            for(let sig of state.signals) {
                let edge = state.edges.get(sig.edgeId);
                if(edge) {
                    let n1 = state.nodes.get(edge.n1), n2 = state.nodes.get(edge.n2);
                    let sx = n1.x + (n2.x - n1.x) * sig.pos, sy = n1.y + (n2.y - n1.y) * sig.pos;
                    ctx.fillStyle = '#1e293b'; ctx.fillRect(sx*gs + 6, sy*gs - 6, 4, 12);
                    ctx.fillStyle = sig.state === 'G' ? CONFIG.colors.sigG : sig.state === 'R' ? CONFIG.colors.sigR : CONFIG.colors.sigY;
                    ctx.beginPath(); ctx.arc(sx*gs + 8, sy*gs, 5, 0, Math.PI*2); ctx.fill();
                }
            }

            // Stations
            for (let stn of state.stations) {
                let sx = stn.x*gs, sy = stn.y*gs;
                ctx.fillStyle = '#1e293b'; ctx.beginPath(); ctx.roundRect(sx - gs*stn.w/2, sy - gs*stn.h/2, gs*stn.w, gs*stn.h, 8); ctx.fill();
                ctx.strokeStyle = '#475569'; ctx.lineWidth = 2; ctx.stroke();
                ctx.fillStyle = '#f8fafc'; ctx.font = '600 14px Inter'; ctx.textAlign = 'center'; ctx.fillText(stn.name, sx, sy + 5);
            }

            // Render Trains from History
            let stepIdx = Math.floor(state.time * 2); // 0.5 step means index = time * 2
            let nxtIdx = Math.ceil(state.time * 2);
            let pct = (state.time * 2) - stepIdx;

            for (let [tId, hist] of state.trainStates) {
                let h1 = hist[stepIdx]; let h2 = hist[nxtIdx] || h1;
                if(!h1) continue; // Not spawned yet or finished
                
                let tDef = state.trainDefs.find(d => d.id === tId);
                let color = tDef.type.includes('Premium') ? CONFIG.colors.trainPre : tDef.type.includes('Express') ? CONFIG.colors.trainExp : CONFIG.colors.trainFrt;
                
                // Interpolate
                let tx = (h1.x + (h2.x - h1.x) * pct) * gs;
                let ty = (h1.y + (h2.y - h1.y) * pct) * gs;
                let angle = h1.angle; // Simple angle
                
                let isSel = state.selectedTrainId === tId; let headSize = isSel ? 1.4 : 1;
                ctx.save(); ctx.translate(tx, ty); ctx.rotate(angle);
                ctx.fillStyle = color; if(isSel) { ctx.shadowColor = color; ctx.shadowBlur = 15; }
                ctx.beginPath(); ctx.roundRect(-12*headSize, -8*headSize, 24*headSize, 16*headSize, 4); ctx.fill();
                ctx.fillStyle = '#0f172a'; ctx.fillRect(4*headSize, -6*headSize, 6*headSize, 12*headSize);
                ctx.restore();
                
                if(state.camera.zoom > 0.6 || isSel) {
                    ctx.textAlign = 'center';
                    let tw = ctx.measureText(tDef.name).width; ctx.fillStyle = 'rgba(15,23,42,0.7)';
                    ctx.beginPath(); ctx.roundRect(tx - tw/2 - 4, ty + 12, tw + 8, 20, 10); ctx.fill();
                    ctx.fillStyle = '#ffffff'; ctx.fillText(tDef.name, tx, ty + 26);
                }
            }

            // Editor Ghost
            if (state.tool === 'track') {
                ctx.fillStyle = 'rgba(56, 189, 248, 0.4)'; ctx.beginPath(); ctx.arc(state.hoveredGrid.x*gs, state.hoveredGrid.y*gs, 8, 0, Math.PI*2); ctx.fill();
                if (state.dragStart) { ctx.strokeStyle = CONFIG.colors.trackGlow; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(state.dragStart.x*gs, state.dragStart.y*gs); ctx.lineTo(state.hoveredGrid.x*gs, state.hoveredGrid.y*gs); ctx.stroke(); }
            } else if (state.tool === 'train') { 
                ctx.fillStyle = 'rgba(245, 158, 11, 0.5)'; ctx.beginPath(); ctx.arc(state.hoveredGrid.x*gs, state.hoveredGrid.y*gs, 15, 0, Math.PI*2); ctx.fill(); 
            }
            
            ctx.restore();
            
            // Weather
            if(state.weather) {
                ctx.fillStyle = 'rgba(15, 23, 42, 0.3)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.strokeStyle = 'rgba(200, 220, 255, 0.4)'; ctx.lineWidth = 1.5; ctx.beginPath();
                for(let p of state.particles) {
                    if(!state.isPaused) { p.y += p.s * CONFIG.simSpeed * dt * 50; p.x += (p.s * 0.2) * CONFIG.simSpeed * dt * 50; if(p.y > canvas.height) { p.y = -10; p.x = Math.random() * canvas.width; } }
                    ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + p.s*0.2, p.y + p.s);
                } ctx.stroke();
            }

            requestAnimationFrame(loop);
        }

        initComplexLayout();
    