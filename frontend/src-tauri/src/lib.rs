use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

/// Épica K (00-research/09-app-nativa-escritorio.md), paso 2: el
/// backend FastAPI empaquetado con PyInstaller corre como sidecar de
/// Tauri (`binaries/pulse-backend-x86_64-pc-windows-msvc.exe`, ver
/// `tauri.conf.json` -> `bundle.externalBin`). Se guarda el handle del
/// proceso hijo para poder matarlo explícitamente al cerrar la
/// ventana - sin esto, cerrar la app dejaría el backend huérfano
/// escuchando en el puerto 8756 indefinidamente.
struct SidecarState(Mutex<Option<CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .manage(SidecarState(Mutex::new(None)))
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      let (mut rx, child) = app
        .shell()
        .sidecar("pulse-backend")
        .expect("no se encontró el sidecar pulse-backend - revisa bundle.externalBin")
        .spawn()
        .expect("no se pudo arrancar el sidecar pulse-backend");

      *app.state::<SidecarState>().0.lock().unwrap() = Some(child);

      // App personal de un único usuario real (Miguel, user_id=3 en
      // la base de datos migrada - ver
      // backend/scripts/migrate_to_sqlite.py): el frontend guarda el
      // id del usuario activo en localStorage tras el onboarding
      // (`useCurrentUser.ts`), pero el WebView de Tauri tiene su
      // propio almacenamiento, aislado del navegador usado en
      // desarrollo (Docker) - sin esto, cada instalación nueva
      // mostraría el formulario de onboarding aunque los datos reales
      // ya existan en la base SQLite. Deliberadamente hardcodeado: no
      // es una app multi-usuario, es la app personal de un único
      // usuario ya conocido. Riesgo aceptado (code-review M-1): si
      // algún día se regenera la base SQLite desde otro origen donde
      // Miguel no sea el id=3, esto quedaría atascado en onboarding -
      // la mitigación sería exponer un `GET /users` en el backend y
      // tomar el primero/único, pero no se justifica para una app de
      // un solo usuario conocido hoy.
      if let Some(window) = app.get_webview_window("main") {
        // Reintenta hasta que el sidecar responda de verdad (arranque
        // en frío de PyInstaller onefile puede tardar varios segundos
        // en extraerse) - un eval() inmediato + reload() sin esperar
        // provocaba una condición de carrera real: `useCurrentUser.ts`
        // borra `pulse_user_id` de localStorage en CUALQUIER fallo de
        // red (no solo 404), así que un intento demasiado pronto
        // dejaba la app atascada en el onboarding para siempre.
        let _ = window.eval(
          "(function retry() {\
             if (localStorage.getItem('pulse_user_id')) return;\
             fetch('http://127.0.0.1:8756/users/3').then(function (r) {\
               if (r.ok) { localStorage.setItem('pulse_user_id', '3'); location.reload(); }\
               else { setTimeout(retry, 500); }\
             }).catch(function () { setTimeout(retry, 500); });\
           })();",
        );
      }

      // Reenvía stdout/stderr del backend al log de Tauri - sin esto,
      // un fallo de arranque del backend (ej. puerto 8756 ya en uso)
      // sería invisible para quien depure la app empaquetada.
      tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
          match event {
            tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
              log::info!("[pulse-backend] {}", String::from_utf8_lossy(&line));
            }
            tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
              log::warn!("[pulse-backend] {}", String::from_utf8_lossy(&line));
            }
            _ => {}
          }
        }
      });

      Ok(())
    })
    .on_window_event(|window, event| {
      if let tauri::WindowEvent::CloseRequested { .. } = event {
        let state = window.state::<SidecarState>();
        let hijo = state.0.lock().unwrap().take();
        if let Some(child) = hijo {
          let _ = child.kill();
        }
      }
    })
    .build(tauri::generate_context!())
    .expect("error while running tauri application")
    .run(|app_handle, event| {
      // Red de seguridad (code-review M-2): `CloseRequested` no cubre
      // TODAS las rutas de salida (ej. `app.exit()` programático, o
      // señales de sistema que Tauri sí intercepta como
      // `RunEvent::Exit`). Sin este segundo punto de limpieza, el
      // sidecar podría quedar huérfano ocupando el puerto 8756 y el
      // siguiente arranque de la app fallaría al hacer bind.
      if let tauri::RunEvent::Exit = event {
        let hijo = app_handle.state::<SidecarState>().0.lock().unwrap().take();
        if let Some(child) = hijo {
          let _ = child.kill();
        }
      }
    });
}
