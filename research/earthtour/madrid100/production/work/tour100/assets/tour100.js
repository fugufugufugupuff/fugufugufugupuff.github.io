(function(){
  var P=window.T100_PINS||[],root=document.querySelector('.t100');if(!root)return;
  var cs=getComputedStyle(root);function col(d){return (cs.getPropertyValue('--d'+d)||'#d7263d').trim()}
  function tile(m){L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(m)}
  function icon(p){return L.divIcon({className:'',iconSize:[30,30],iconAnchor:[15,30],html:'<div class="pin" style="background:'+col(p.day)+'"><span>'+p.label+'</span></div>'})}
  function go(){
    document.querySelectorAll('.t100 .spot .map').forEach(function(el){
      if(el._done)return;el._done=1;el.innerHTML='';
      var lat=+el.dataset.lat,lng=+el.dataset.lng,r=+el.dataset.r||300;
      var m=L.map(el,{scrollWheelZoom:false,zoomControl:false,attributionControl:true});tile(m);
      var c=getComputedStyle(el).getPropertyValue('--dc').trim()||'#d7263d';
      L.circle([lat,lng],{radius:r,color:c,weight:2,fillColor:c,fillOpacity:.15}).addTo(m);
      L.circleMarker([lat,lng],{radius:6,color:'#fff',weight:2,fillColor:c,fillOpacity:1}).addTo(m);
      m.setView([lat,lng],r>1500?13:r>600?15:16);
    });
    var all=document.getElementById('t100-map-all');
    if(all&&!all._done&&P.length){all._done=1;all.innerHTML='';
      var m=L.map(all,{scrollWheelZoom:false});tile(m);var by={};
      P.forEach(function(p){(by[p.day]=by[p.day]||[]).push([p.lat,p.lng])});
      Object.keys(by).forEach(function(d){L.polyline(by[d],{color:col(d),weight:4,dashArray:'6 8',opacity:.85}).addTo(m)});
      var g=L.featureGroup(P.map(function(p){return L.marker([p.lat,p.lng],{icon:icon(p)}).bindPopup('<b>DAY'+p.day+'　'+p.time+'</b><br>'+p.name+'<br><a href="#'+p.anchor+'">この食事へ</a>')}));
      g.addTo(m);m.fitBounds(g.getBounds().pad(.12));
    }
  }
  function fallback(){
    document.querySelectorAll('.t100 .spot .map').forEach(function(el){if(el._done)return;el._done=1;var a=+el.dataset.lat,b=+el.dataset.lng,d=.006;
      el.innerHTML='<div class="mapfb"><iframe loading="lazy" src="https://www.openstreetmap.org/export/embed.html?bbox='+(b-d)+','+(a-d)+','+(b+d)+','+(a+d)+'&layer=mapnik&marker='+a+','+b+'"></iframe></div>'});
    var all=document.getElementById('t100-map-all');if(all&&!all._done&&P.length){all._done=1;
      var la=P.map(function(p){return p.lat}),ln=P.map(function(p){return p.lng});
      all.innerHTML='<div class="mapfb"><iframe loading="lazy" src="https://www.openstreetmap.org/export/embed.html?bbox='+(Math.min.apply(0,ln)-.02)+','+(Math.min.apply(0,la)-.02)+','+(Math.max.apply(0,ln)+.02)+','+(Math.max.apply(0,la)+.02)+'&layer=mapnik"></iframe></div>'}
  }
  function start(){if(window.L){go()}else{var s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';s.onload=go;s.onerror=fallback;document.head.appendChild(s);setTimeout(function(){if(!window.L)fallback()},7000)}}
  if('IntersectionObserver' in window){var io=new IntersectionObserver(function(es){if(es.some(function(e){return e.isIntersecting})){io.disconnect();start()}},{rootMargin:'600px'});
    document.querySelectorAll('.t100 .map,#t100-map-all').forEach(function(el){io.observe(el)})}else{start()}
})();
