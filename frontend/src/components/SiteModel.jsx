import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { apiBase } from '../api'

function masonryTexture(kind) {
  const canvas=document.createElement('canvas'); canvas.width=canvas.height=256
  const ctx=canvas.getContext('2d'); ctx.fillStyle=kind==='ground'?'#aaa998':'#d8d1c3';ctx.fillRect(0,0,256,256)
  let seed=9173
  const random=()=>{seed=(seed*16807)%2147483647;return(seed-1)/2147483646}
  for(let i=0;i<2200;i++){const shade=Math.floor(120+random()*100);ctx.fillStyle=`rgba(${shade},${shade},${shade},.18)`;ctx.fillRect(random()*256,random()*256,1+random()*3,1+random()*2)}
  if(kind!=='ground') for(let y=0;y<256;y+=32){ctx.strokeStyle='#8f877666';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(256,y);ctx.stroke();for(let x=(y/32%2)*32;x<256;x+=64){ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x,y+32);ctx.stroke()}}
  const texture=new THREE.CanvasTexture(canvas);texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.colorSpace=THREE.SRGBColorSpace
  return texture
}

export default function SiteModel({ asset }) {
  const host = useRef(null)
  const reset = useRef(() => {})
  const [failure, setFailure] = useState('')
  const [ready, setReady] = useState(false)
  useEffect(() => {
    let stopped = false, renderer, controls, resize, frame
    const scene = new THREE.Scene()
    const group = new THREE.Group()
    const el = host.current
    const disposeObject = object => object.traverse(child => {
      child.geometry?.dispose()
      const materials = Array.isArray(child.material) ? child.material : [child.material]
      materials.filter(Boolean).forEach(material => {
        Object.values(material).filter(v => v?.isTexture).forEach(t => t.dispose())
        material.dispose()
      })
    })
    // Synchronize loading state with the external WebGL renderer lifecycle.
    // oxlint-disable-next-line react/set-state-in-effect
    setFailure(''); setReady(false)
    try {
      scene.background = new THREE.Color('#e9eee5')
      renderer = new THREE.WebGLRenderer({ antialias: true })
      renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap
      renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.15
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.domElement.setAttribute('aria-label', 'Interactive 3D heritage model')
      renderer.domElement.setAttribute('role', 'img')
      el.appendChild(renderer.domElement)
      const camera = new THREE.PerspectiveCamera(40, 1, .01, 100000)
      controls = new OrbitControls(camera, renderer.domElement)
      controls.enableDamping = true
      scene.add(new THREE.HemisphereLight(0xe6efff, 0x655b43, 1.8))
      const sunlight = new THREE.DirectionalLight(0xffe3b4, 3.6)
      sunlight.position.set(-60,110,65); sunlight.castShadow=true; sunlight.shadow.mapSize.set(2048,2048)
      Object.assign(sunlight.shadow.camera,{left:-110,right:110,top:110,bottom:-110,near:.1,far:400})
      sunlight.shadow.bias=-.0004; sunlight.shadow.normalBias=.08
      scene.add(sunlight); scene.add(group)
      function fit() {
        const box = new THREE.Box3().setFromObject(group)
        if (box.isEmpty()) throw new Error('Model contains no visible geometry')
        const center = box.getCenter(new THREE.Vector3())
        const size = Math.max(...box.getSize(new THREE.Vector3()).toArray()) || 1
        if (!Number.isFinite(size)) throw new Error('Invalid model bounds')
        camera.near = size / 1000; camera.far = size * 100
        camera.aspect=el.clientWidth/Math.max(el.clientHeight,1)
        const direction=new THREE.Vector3(.7,.55,.9).normalize()
        const right=new THREE.Vector3().crossVectors(new THREE.Vector3(0,1,0),direction).normalize()
        const up=new THREE.Vector3().crossVectors(direction,right)
        const vertical=Math.tan(THREE.MathUtils.degToRad(camera.fov/2)),horizontal=vertical*camera.aspect
        let distance=0
        for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
          const offset=new THREE.Vector3(x,y,z).sub(center)
          distance=Math.max(distance,offset.dot(direction)+Math.abs(offset.dot(right))/horizontal,offset.dot(direction)+Math.abs(offset.dot(up))/vertical)
        }
        camera.position.copy(center).addScaledVector(direction,distance*1.06)
        controls.target.copy(center); controls.maxDistance = size*10; controls.minDistance = size*.1
        camera.updateProjectionMatrix(); controls.update()
        setReady(true)
      }
      reset.current = fit
      if (asset.kind === 'glb') {
        new GLTFLoader().load(apiBase + asset.url, gltf => {
          if (stopped) { disposeObject(gltf.scene); return }
          try { group.add(gltf.scene); fit() } catch (e) { setFailure(e.message) }
        }, undefined, e => { if (!stopped) setFailure(`Model could not be rendered: ${e.message || 'unsupported geometry'}`) })
      } else {
        const textures={stone:masonryTexture('stone'),paving:masonryTexture('paving'),ground:masonryTexture('ground')}
        const materials=new Map()
        for (const p of asset.scene.parts) {
          const geometry = p.shape === 'cylinder' ? new THREE.CylinderGeometry(...p.size) : p.shape === 'sphere' ? new THREE.SphereGeometry(p.size[0], 24, 16) : new THREE.BoxGeometry(...p.size)
          const kind=p.material || 'stone'; const key=`${p.color}-${kind}`
          if(!materials.has(key)) materials.set(key,new THREE.MeshStandardMaterial({color:p.color,roughness:kind==='water'?.25:.92,
            map:textures[kind] || null,bumpMap:textures[kind] || null,bumpScale:kind==='ground'?.08:.055,metalness:kind==='water'?.2:0}))
          const mesh = new THREE.Mesh(geometry, materials.get(key))
          mesh.position.set(...p.position); if(p.rotation)mesh.rotation.set(...p.rotation); if(p.scale)mesh.scale.set(...p.scale)
          mesh.castShadow=p.shadow!==false && kind!=='ground' && kind!=='water';mesh.receiveShadow=true;group.add(mesh)
        }
        // Separate outline inset, normalized to a 50-unit square. It is not the
        // building's surveyed plan and is never used to imply metric precision.
        const rings = asset.scene.footprint?.rings_m || []
        if (rings.length) {
          const points = rings.flat(); const xs = points.map(p => p[0]), ys = points.map(p => p[1])
          const minX = Math.min(...xs), minY = Math.min(...ys)
          const scale = 45 / Math.max(Math.max(...xs)-minX, Math.max(...ys)-minY, 1)
          for (const ring of rings) {
            const geometry = new THREE.BufferGeometry().setFromPoints(ring.map(([x,y]) => new THREE.Vector3((x-minX)*scale+32, 0, -(y-minY)*scale+22)))
            group.add(new THREE.LineLoop(geometry, new THREE.LineBasicMaterial({ color: '#295c56' })))
          }
        }
        fit()
      }
      resize = new ResizeObserver(() => {
        const w = el.clientWidth, h = el.clientHeight
        if (!w || !h) return
        renderer.setSize(w, h); camera.aspect = w/h; camera.updateProjectionMatrix()
      })
      resize.observe(el)
      const draw = () => { if (stopped) return; controls.update(); renderer.render(scene, camera); frame = requestAnimationFrame(draw) }
      draw()
    } catch (e) { setFailure(`3D unavailable: ${e.message}`) }
    return () => {
      stopped = true; cancelAnimationFrame(frame); resize?.disconnect(); controls?.dispose()
      disposeObject(scene); renderer?.dispose(); renderer?.forceContextLoss(); el.replaceChildren()
    }
  }, [asset])
  return <div className="model-view"><div className="model-status"><span className="badge amber">{asset.confidence}</span><button className="text-button" disabled={!ready} onClick={() => reset.current()}>Reset camera</button></div><div ref={host} className="model-canvas" />{failure && <p className="error" role="alert">{failure}</p>}<p className="viewer-help">Drag to orbit · scroll to zoom · right-drag to pan</p><p>{asset.caveat}</p>{asset.scene && <p>{asset.scene.height_basis}{asset.scene.footprint && ' The separate green outline shows OSM mapped geometry at an independent display scale.'}</p>}</div>
}
