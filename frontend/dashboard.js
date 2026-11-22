const API=(window.BOLOKHATA_API_URL||((["localhost","127.0.0.1"].includes(location.hostname)&&location.port&&location.port!=="8000")?"http://127.0.0.1:8000":location.origin)).replace(/\/$/,"");const token=sessionStorage.getItem("bolokhaata_token")||localStorage.getItem("bolokhaata_token");const money=n=>new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0}).format(Number(n||0));const $=id=>document.getElementById(id);if(!token)location.replace("auth.html?mode=login");async function loadDashboard(){try{const [meRes,sumRes]=await Promise.all([fetch(API+"/api/v1/auth/me",{headers:{Authorization:"Bearer "+token}}),fetch(API+"/api/v1/dashboard/summary",{headers:{Authorization:"Bearer "+token}})]);if(meRes.status===401||sumRes.status===401)throw new Error("Your session has expired. Please sign in again.");if(!meRes.ok||!sumRes.ok)throw new Error("The business API is unavailable. Please check that the backend is running and configured.");const me=await meRes.json(),s=await sumRes.json();const name=me.full_name||"there";$("greeting").textContent="Namaste, "+name+"!";$("sideName").textContent=name;$("sideBusiness").textContent=me.business_name||"Your business";$("avatar").textContent=name.split(/\s+/).map(x=>x[0]).slice(0,2).join("").toUpperCase();$("businessLine").textContent=(me.business_name?me.business_name+" · ":"")+"Here’s how your business is doing."; $("todaySales").textContent=money(s.today_sales??0);$("monthSales").textContent=money(s.month_sales??s.total_sales??0);$("outstanding").textContent=money(s.total_outstanding_udhar??0);$("expenses").textContent=money(s.total_expenses??0);const rows=s.recent_transactions||[];$("activity").innerHTML=rows.length?"":"<p class='empty'>No transactions recorded yet. Start with a voice entry or create an invoice.</p>";rows.forEach(t=>{const row=document.createElement("div");row.className="activity-row";const left=document.createElement("span"),title=document.createElement("b"),sub=document.createElement("small"),amount=document.createElement("strong");title.textContent=t.notes||t.type||"Business entry";sub.textContent=t.date?new Date(t.date).toLocaleString():"Recorded transaction";amount.textContent=money(t.amount);left.append(title,sub);row.append(left,amount);$("activity").append(row)})}catch(e){$("dashError").textContent=e.message;$("todaySales").textContent=$("monthSales").textContent=$("outstanding").textContent=$("expenses").textContent="—"}}loadDashboard();$("logout").addEventListener("click",()=>{sessionStorage.removeItem("bolokhaata_token");localStorage.removeItem("bolokhaata_token");location.href="auth.html"});let recognition=null;
let draft=null;
const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;
const micButton=$("micBtn");
const voiceStatus=$("voiceStatus");
const voiceText=$("voiceText");
const parseButton=$("parseVoiceText");
function setVoiceStatus(message){if(voiceStatus)voiceStatus.textContent=message}
async function parseVoiceTranscript(transcript){
 const clean=(transcript||"").trim();
 if(clean.length<2){setVoiceStatus("Please speak or type a complete transaction.");return}
 $("transcript").textContent=clean;
 setVoiceStatus("Understanding your entry…");
 if(parseButton)parseButton.disabled=true;
 try{
  const res=await fetch(API+"/api/v1/voice/parse",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:JSON.stringify({transcript:clean})});
  const data=await res.json().catch(()=>({}));
  if(!res.ok)throw new Error(data.detail||"I couldn't understand that entry. Please try again or edit the text.");
  draft=data;
  $("draftCustomer").value=data.customer_name||"";
  $("draftAmount").value=data.amount||"";
  $("draftKind").value=data.transaction_type||"SALE";
  $("draftPanel").hidden=false;
  $("draftPanel").scrollIntoView({behavior:"smooth",block:"nearest"});
  setVoiceStatus("Draft ready. Check the customer, amount and entry type, then confirm.");
 }catch(error){setVoiceStatus(error.message)}
 finally{if(parseButton)parseButton.disabled=false}
}
if(micButton){
 micButton.addEventListener("click",()=>{
  if(!window.isSecureContext && !["localhost","127.0.0.1"].includes(location.hostname)){
   setVoiceStatus("Microphone access requires HTTPS. Open the secure deployed website or type your entry below.");return;
  }
  if(!Speech){setVoiceStatus("Speech recognition is unavailable in this browser. Type your transaction below and select Understand entry.");return}
  if(recognition){recognition.stop();return}
  try{
   recognition=new Speech();
   const language=localStorage.getItem("bolokhata_lang")||"hi";
   recognition.lang=language==="en"?"en-IN":"hi-IN";
   recognition.interimResults=true;
   recognition.continuous=false;
   recognition.maxAlternatives=3;
   let finalTranscript="";
   setVoiceStatus("Listening… Say the customer's name, amount and whether it is a sale, udhar or expense.");
   micButton.textContent="■  Stop listening";
   recognition.onresult=event=>{
    let interim="";
    for(let i=event.resultIndex;i<event.results.length;i++){
     const spoken=event.results[i][0].transcript;
     if(event.results[i].isFinal)finalTranscript+=spoken+" ";
     else interim+=spoken;
    }
    if(voiceText)voiceText.value=(finalTranscript+interim).trim();
    if(finalTranscript.trim())setVoiceStatus("Heard: "+(finalTranscript+interim).trim());
   };
   recognition.onerror=event=>{
    const messages={"not-allowed":"Microphone permission was denied. Allow microphone access in your browser, or type the entry below.", "audio-capture":"No microphone was found. Connect a microphone or type the entry below.", "no-speech":"No speech was detected. Please try again and speak a little louder.", network:"Speech recognition network error. Please try again or type the entry below."};
    setVoiceStatus(messages[event.error]||("Speech recognition stopped: "+event.error+". You can type the entry below."));
   };
   recognition.onend=()=>{
    micButton.textContent="🎙  Start voice entry";
    const heard=(finalTranscript||(voiceText&&voiceText.value)||"").trim();
    if(heard.length>=2){if(voiceText)voiceText.value=heard;parseVoiceTranscript(heard)}
    recognition=null;
   };
   recognition.start();
  }catch(error){recognition=null;micButton.textContent="🎙  Start voice entry";setVoiceStatus("Could not start the microphone. Check browser permission, or type the entry below.")}
 });
}
if(parseButton)parseButton.addEventListener("click",()=>parseVoiceTranscript(voiceText&&voiceText.value));
if(voiceText)voiceText.addEventListener("keydown",event=>{if((event.ctrlKey||event.metaKey)&&event.key==="Enter")parseVoiceTranscript(voiceText.value)});
$("dismissDraft").addEventListener("click",()=>{$("draftPanel").hidden=true;draft=null;setVoiceStatus("Draft discarded. Nothing was saved.")});
$("confirmDraft").addEventListener("click",async()=>{
 const amount=Number($("draftAmount").value);
 if(!Number.isFinite(amount)||amount<=0){setVoiceStatus("Enter a valid amount before saving.");return}
 const button=$("confirmDraft");button.disabled=true;
 try{
  const response=await fetch(API+"/api/v1/voice/confirm",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:JSON.stringify({kind:$("draftKind").value,amount,customer_name:$("draftCustomer").value.trim()||null,notes:$("transcript").textContent})});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(data.detail||"Could not save transaction");
  $("draftPanel").hidden=true;setVoiceStatus("Transaction saved successfully.");draft=null;
  if(voiceText)voiceText.value="";
  await loadDashboard();
 }catch(e){setVoiceStatus(e.message)}
 finally{button.disabled=false}
});