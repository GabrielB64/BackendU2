(function(){
    const switcher=document.getElementById("themeSwitch");
    function apply(theme){
        document.documentElement.setAttribute("data-bs-theme",theme);
        localStorage.setItem("theme",theme);
        if(switcher) switcher.checked=theme==="dark";
    }
    const saved=localStorage.getItem("theme");
    if(saved) apply(saved);
    else apply(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");
    if(switcher) switcher.addEventListener("change",()=>apply(switcher.checked?"dark":"light"));
})();
