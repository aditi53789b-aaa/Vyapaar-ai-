document.addEventListener("DOMContentLoaded",()=>{
 const token=sessionStorage.getItem("bolokhaata_token")||localStorage.getItem("bolokhaata_token");
 if(!token){location.replace("auth.html?mode=login");return}
 const api=(window.BOLOKHATA_API_URL||location.origin).replace(/\/$/,"");
 fetch(api+"/api/v1/auth/me",{headers:{Authorization:"Bearer "+token}})
  .then(response=>{if(response.status===401){location.replace("auth.html?mode=login");throw new Error("Session expired")}if(!response.ok)throw new Error("Profile unavailable");return response.json()})
  .then(user=>{
   const name=user.full_name||"Your account";
   const nameEl=document.getElementById("invoiceUser");
   const businessEl=document.getElementById("invoiceBusiness");
   const avatarEl=document.getElementById("invoiceAvatar");
   if(nameEl)nameEl.textContent=name;
   if(businessEl)businessEl.textContent=user.business_name||"Business profile";
   if(avatarEl)avatarEl.textContent=name.split(/\s+/).map(part=>part[0]).slice(0,2).join("").toUpperCase();
  }).catch(()=>{});
 const logout=document.getElementById("invoiceLogout");
 if(logout)logout.addEventListener("click",()=>{
  sessionStorage.removeItem("bolokhaata_token");
  localStorage.removeItem("bolokhaata_token");
  location.href="auth.html";
 });
});