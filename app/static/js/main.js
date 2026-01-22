// app/static/js/main.js
async function eliminarCliente(id) {
  if (!confirm("¿Seguro que quieres eliminar este cliente?")) return;
  try {
    const resp = await fetch(`/clientes/${id}`, {
      method: 'DELETE',
      headers: { 'Accept': 'application/json' }
    });
    const data = await resp.json().catch(() => null);
    if (data && data.redirect) {
      window.location = data.redirect;
      return;
    }
    if (resp.ok && data && data.mensaje) {
      const row = document.getElementById(`cliente-row-${id}`);
      if (row) row.remove();
      mostrarToast(data.mensaje);
      return;
    }
    window.location = '/error404';
  } catch (err) {
    console.error(err);
    window.location = '/error404';
  }
}

function mostrarToast(msg) {
  const el = document.createElement('div');
  el.textContent = msg;
  Object.assign(el.style, { position:'fixed', right:'20px', bottom:'20px', background:'#198754', color:'#fff', padding:'10px 14px', borderRadius:'6px', zIndex:9999 });
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

document.addEventListener('click', function (e) {
  const btn = e.target.closest && e.target.closest('.btn-eliminar-cliente');
  if (!btn) return;
  const id = btn.dataset.id;
  if (!id) return;
  eliminarCliente(id);
});