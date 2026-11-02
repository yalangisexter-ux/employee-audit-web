/* Cloud sync for EXE/mobile encrypted snapshots */
const SYNC_WORKER_URL="https://raw-strength-audit-db-sync.yalangisexter.workers.dev";
const SNAPSHOT_AAD=new TextEncoder().encode("RawStrengthEmployeeAuditManager:encrypted-customer-database:v1");
async function decompressZlib(bytes){
  try{
    const ds=new DecompressionStream("deflate");
    return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(ds)).arrayBuffer());
  }catch(_){
    const ds=new DecompressionStream("deflate-raw");
    return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(ds)).arrayBuffer());
  }
}
async function pullCloudSync(){
  const secret=(document.getElementById("syncSecret")?.value||"").trim();
  const installId=(document.getElementById("syncInstallId")?.value||"").trim();
  const statusEl=document.getElementById("syncStatus");
  if(!secret||!installId){alert("Enter Installation ID and Sync Secret from EXE Master Customer Mode.");return;}
  localStorage.setItem("eaw_install_id",installId);
  localStorage.setItem("eaw_sync_secret",secret);
  if(statusEl)statusEl.textContent="Registering device...";
  try{
    let deviceId=localStorage.getItem("eaw_device_id")||crypto.randomUUID().replace(/-/g,"");
    let deviceSecret=localStorage.getItem("eaw_device_secret")||(crypto.randomUUID()+crypto.randomUUID()).replace(/-/g,"");
    localStorage.setItem("eaw_device_id",deviceId);
    localStorage.setItem("eaw_device_secret",deviceSecret);
    const reg=await fetch(SYNC_WORKER_URL+"/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({installation_id:installId,device_id:deviceId,device_secret:deviceSecret})});
    if(!reg.ok)throw new Error("Register failed HTTP "+reg.status);
    const regBody=await reg.json();
    const token=regBody.token||regBody.device_token;
    if(!token)throw new Error("No device token");
    if(statusEl)statusEl.textContent="Pulling encrypted snapshot...";
    const res=await fetch(SYNC_WORKER_URL+"/pull",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:JSON.stringify({prefer_latest:true})});
    if(res.status===404)throw new Error("No remote snapshot. Open EXE with Master Customer Mode sync once.");
    if(!res.ok)throw new Error("Pull failed HTTP "+res.status);
    const encryptedBytes=new Uint8Array(await res.arrayBuffer());
    if(encryptedBytes.length<34)throw new Error("Invalid snapshot");
    const salt=encryptedBytes.slice(6,22);
    const iv=encryptedBytes.slice(22,34);
    const header=encryptedBytes.slice(0,34);
    const ciphertext=encryptedBytes.slice(34);
    const enc=new TextEncoder();
    const baseKey=await crypto.subtle.importKey("raw",enc.encode(secret),"PBKDF2",false,["deriveKey"]);
    const aesKey=await crypto.subtle.deriveKey({name:"PBKDF2",salt,iterations:300000,hash:"SHA-256"},baseKey,{name:"AES-GCM",length:256},false,["decrypt"]);
    const aad=new Uint8Array(header.length+SNAPSHOT_AAD.length);aad.set(header,0);aad.set(SNAPSHOT_AAD,header.length);
    const decryptedBuffer=await crypto.subtle.decrypt({name:"AES-GCM",iv,additionalData:aad,tagLength:128},aesKey,ciphertext);
    const decompressed=await decompressZlib(new Uint8Array(decryptedBuffer));
    const markerStr="\n__RSC_JSON__\n";
    const marker=enc.encode(markerStr);
    let markerIdx=-1;
    for(let i=0;i<=decompressed.length-marker.length;i++){let ok=true;for(let j=0;j<marker.length;j++){if(decompressed[i+j]!==marker[j]){ok=false;break;}}if(ok){markerIdx=i;break;}}
    let pulled=null;
    if(markerIdx!==-1)pulled=JSON.parse(new TextDecoder().decode(decompressed.slice(markerIdx+marker.length)));
    else pulled=JSON.parse(new TextDecoder().decode(decompressed));
    let attendanceList=[];
    if(Array.isArray(pulled.attendance))attendanceList=pulled.attendance;
    else if(pulled.attendance&&typeof pulled.attendance==="object"){
      for(const [key,rec] of Object.entries(pulled.attendance)){
        const parts=String(key).split("_");
        attendanceList.push({...rec,employee_name:rec.employee_name||rec.name||"",work_date:rec.work_date||rec.date||parts.slice(1).join("_")||""});
      }
    }
    const empById={};
    for(const e of (pulled.employees||[])){if(e.id!=null)empById[e.id]=e.name||e.employee_name||"";}
    const tasks=(pulled.tasks||[]).map(t=>({...t,assignee:t.assignee||empById[t.employee_id]||t.employee_name||"",due_date:t.due_date||t.task_date||""}));
    if(statusEl)statusEl.textContent=`Importing ${(pulled.employees||[]).length} employees, ${tasks.length} tasks...`;
    const out=await api("/api/sync/import",{method:"POST",body:JSON.stringify({employees:pulled.employees||[],tasks,attendance:attendanceList,clear_existing:true})});
    if(statusEl)statusEl.textContent="Imported: "+JSON.stringify(out.imported);
    notice("Cloud data imported");
    await loadTab();
  }catch(err){
    if(statusEl)statusEl.textContent="Sync error: "+err.message;
    alert("Cloud sync: "+err.message);
  }
}
