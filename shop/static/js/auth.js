function showToast(message, type="info") {
    let container=document.getElementById("toast-container");
    if(!container){
        container=document.createElement("div");
        container.id="toast-container";
        container.className="toast-container position-fixed bottom-0 end-0 p-3";
        document.body.appendChild(container);
    }
    const el=document.createElement("div");
    el.className=`toast align-items-center text-bg-${type} border-0`;
    el.setAttribute("role","alert");
    el.innerHTML=`<div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    container.appendChild(el);
    const toast=new bootstrap.Toast(el,{delay:3500});
    toast.show();
    el.addEventListener("hidden.bs.toast",()=>el.remove());
}

function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_type");
    window.location.href="/";
}

async function updateCartCounter() {
    const token=localStorage.getItem("access_token");
    const counter=document.getElementById("cart-counter");
    if(!counter) return;
    if(!token){counter.textContent="0";return;}
    try {
        const r=await fetch("/api/cart/",{headers:{"Authorization":`Bearer ${token}`}});
        if(!r.ok){counter.textContent="0";return;}
        const cart=await r.json();
        counter.textContent=cart.items.reduce((sum,i)=>sum+i.quantity,0);
    } catch { counter.textContent="0"; }
}

document.addEventListener("DOMContentLoaded",()=>{
    const area=document.getElementById("auth-buttons");
    if(!area)return;
    const token=localStorage.getItem("access_token");
    const type=localStorage.getItem("user_type");
    if(token){
        area.innerHTML=type==="COMPANY"
            ? '<a href="/company/dashboard/" class="btn btn-outline-primary btn-sm me-1">Dashboard</a><button onclick="logout()" class="btn btn-outline-danger btn-sm">Salir</button>'
            : '<button onclick="logout()" class="btn btn-outline-danger btn-sm">Salir</button>';
    } else {
        area.innerHTML='<a href="/login/client/" class="btn btn-outline-primary btn-sm me-1">Ingresar</a><a href="/register/client/" class="btn btn-primary btn-sm">Registrarse</a>';
    }
    updateCartCounter();
});
