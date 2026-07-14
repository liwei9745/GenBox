/* 远程 chatgpt2api 同步前端逻辑（依赖 app-all.js 的 _authFetch / _adminKey） */
(function () {
  "use strict";

  var state = {
    deploymentId: "",
    candidates: [],   // 原始候选（来自预览）
    filtered: [],     // 当前筛选后可见
  };
  var lastFocusedElement = null;

  function $(id) { return document.getElementById(id); }

  function setDeployStatus(message, type) {
    var el = $("syncDeployStatus");
    if (!el) return;
    el.textContent = message || "";
    el.className = "sync-status" + (type ? " " + type : "");
  }

  function readJson(r) {
    return r.json().catch(function () { return {}; }).then(function (data) {
      if (!r.ok) throw new Error(data.detail || data.error || ("HTTP " + r.status));
      return data;
    });
  }

  function fmtDate(d) {
    var y = d.getFullYear();
    var m = ("0" + (d.getMonth() + 1)).slice(-2);
    var day = ("0" + d.getDate()).slice(-2);
    return y + "-" + m + "-" + day;
  }

  function dateRangeParams() {
    var mode = $("syncDateRange").value;
    if (!mode) return { start_date: "", end_date: "" };
    var now = new Date();
    if (mode === "today") {
      return { start_date: fmtDate(now), end_date: fmtDate(now) };
    }
    if (mode === "month") {
      var first = new Date(now.getFullYear(), now.getMonth(), 1);
      return { start_date: fmtDate(first), end_date: fmtDate(now) };
    }
    if (mode === "custom") {
      return {
        start_date: $("syncDateStart").value || "",
        end_date: $("syncDateEnd").value || "",
      };
    }
    return { start_date: "", end_date: "" };
  }

  window.openSyncModal = function () {
    lastFocusedElement = document.activeElement;
    $("syncModal").classList.add("show");
    document.body.style.overflow = "hidden";
    loadSyncDeployments();
    $("syncPreview").innerHTML =
      i18nText('sync.instructions_html');
    setTimeout(function () { $("syncModal").querySelector(".modal-close").focus(); }, 0);
  };

  window.closeSyncModal = function () {
    $("syncModal").classList.remove("show");
    document.body.style.overflow = "";
    if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
      lastFocusedElement.focus();
    }
  };

  document.addEventListener("keydown", function (event) {
    var modal = $("syncModal");
    if (!modal || !modal.classList.contains("show")) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeSyncModal();
      return;
    }
    if (event.key !== "Tab") return;
    var focusable = modal.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  function loadSyncDeployments(selectedId) {
    _authFetch("/api/sync/deployments")
      .then(readJson)
      .then(function (d) {
        var deps = d.deployments || [];
        var box = $("syncDeployments");
        if (!deps.length) {
          box.innerHTML = i18nText('sync.no_deployment_html');
        } else {
          box.innerHTML = deps.map(function (dep) {
            return (
              '<div class="sync-dep-row">' +
              '<span class="sync-dep-name">' + esc(dep.name) + "</span>" +
              '<span class="sync-dep-url">' + esc(dep.base_url) + "</span>" +
              '<button class="btn-ghost btn-sm" onclick="testSyncDeployment(\'' +
              dep.id + "',this)\">" + i18nText('common.test') + "</button>" +
              '<button class="btn-ghost btn-sm sync-delete-btn" onclick="deleteSyncDeployment(\'' +
              dep.id + "')\">" + i18nText('common.delete') + "</button>" +
              "</div>"
            );
          }).join("");
        }
        var sel = $("syncDepSelect");
        sel.innerHTML =
          '<option value="">' + i18nText('sync.choose_deployment') + '</option>' +
          deps.map(function (dep) {
            return '<option value="' + dep.id + '">' + esc(dep.name) + "</option>";
          }).join("");
        if (selectedId) sel.value = selectedId;
      })
      .catch(function (e) {
        $("syncDeployments").innerHTML = i18nText('sync.load_failed_html');
        setDeployStatus(i18nText('common.load_failed_prefix') + e.message, "error");
      });
  }

  window.saveSyncDeployment = function () {
    var name = $("syncDepName").value.trim();
    var url = $("syncDepUrl").value.trim();
    var key = $("syncDepKey").value;
    if (!url) { alert(i18nText('sync.url_required')); return; }
    setDeployStatus(i18nText('sync.saving'), "");
    _authFetch("/api/sync/deployments", {
      method: "POST",
      body: JSON.stringify({ name: name, base_url: url, api_key: key }),
    })
      .then(readJson)
      .then(function (d) {
        $("syncDepName").value = "";
        $("syncDepUrl").value = "";
        $("syncDepKey").value = "";
        setDeployStatus(i18nText('sync.saved'), "success");
        loadSyncDeployments(d.deployment && d.deployment.id);
      })
      .catch(function (e) { setDeployStatus(i18nText('common.save_failed_colon') + e.message, "error"); });
  };

  window.deleteSyncDeployment = function (id) {
    if (!confirm(i18nText('sync.delete_confirm'))) return;
    _authFetch("/api/sync/deployments/" + id, { method: "DELETE" })
      .then(readJson)
      .then(function () { loadSyncDeployments(); })
      .catch(function (e) { setDeployStatus(i18nText('common.delete_failed_colon') + e.message, "error"); });
  };

  window.testSyncDeployment = function (id, button) {
    var oldText = button ? button.textContent : i18nText('common.test');
    if (button) { button.disabled = true; button.textContent = i18nText('sync.testing'); }
    _authFetch("/api/sync/test", {
      method: "POST",
      body: JSON.stringify({ deployment_id: id }),
    })
      .then(readJson)
      .then(function (d) {
        if (d.ok) {
          alert(i18nText('sync.connection_success') + (d.version || i18nText('sync.unknown')) + i18nText('sync.role_prefix') + (d.role || i18nText('sync.unknown')));
        } else {
          alert(i18nText('sync.connection_failed_prefix') + (d.error || i18nText('sync.unknown_error')));
        }
      })
      .catch(function (e) { alert(i18nText('sync.test_error_prefix') + e.message); })
      .finally(function () {
        if (button) { button.disabled = false; button.textContent = oldText; }
      });
  }

  window.loadSyncPreview = function () {
    var id = $("syncDepSelect").value;
    state.deploymentId = id;
    if (!id) {
      $("syncPreview").innerHTML =
        i18nText('sync.choose_first_html');
      return;
    }
    var dr = dateRangeParams();
    $("syncPreview").innerHTML = i18nText('sync.loading_remote_html');
    _authFetch("/api/sync/preview", {
      method: "POST",
      body: JSON.stringify({
        deployment_id: id,
        start_date: dr.start_date,
        end_date: dr.end_date,
      }),
    })
      .then(readJson)
      .then(function (d) {
        state.candidates = d.candidates || [];
        applySyncFilters();
      })
      .catch(function (e) {
        $("syncPreview").innerHTML =
          i18nText('sync.preview_failed_html') + esc(e.message) + "</div>";
      });
  };

  window.testInlineSyncDeployment = function () {
    var url = $("syncDepUrl").value.trim();
    var key = $("syncDepKey").value;
    if (!url) { alert(i18nText('sync.url_required')); return; }
    _authFetch("/api/sync/test", {
      method: "POST",
      body: JSON.stringify({ base_url: url, api_key: key }),
    })
      .then(readJson)
      .then(function (d) {
        alert(d.ok
          ? i18nText('sync.connection_success') + (d.version || i18nText('sync.unknown')) + i18nText('sync.role_prefix') + (d.role || i18nText('sync.unknown'))
          : i18nText('sync.connection_failed_prefix') + (d.error || i18nText('sync.unknown_error')));
      })
      .catch(function (e) { alert(i18nText('sync.test_error_prefix') + e.message); });
  };

  window.onSyncDateRangeChange = function () {
    var custom = $("syncDateRange").value === "custom";
    $("syncDateStart").classList.toggle("hidden", !custom);
    $("syncDateEnd").classList.toggle("hidden", !custom);
    if (!custom) loadSyncPreview();
  };

  window.applySyncFilters = function () {
    var aspect = $("syncAspect").value;
    var size = $("syncSize").value;
    var list = state.candidates.filter(function (c) {
      if (aspect && c.aspect !== aspect) return false;
      if (size && !matchSize(c.size || 0, size)) return false;
      return true;
    });
    state.filtered = list;
    renderCandidates(list);
  };

  function matchSize(bytes, bucket) {
    var mb = bytes / (1024 * 1024);
    if (bucket === "small") return mb < 1;
    if (bucket === "mid") return mb >= 1 && mb <= 5;
    if (bucket === "large") return mb > 5;
    return true;
  }

  function renderCandidates(list) {
    var box = $("syncPreview");
    if (!list.length) {
      box.innerHTML = i18nText('sync.no_new_html');
      updateCounts();
      return;
    }
    box.innerHTML = list.map(function (c, i) {
      var selectable = c.status === "new";
      var badge = "";
      if (c.status === "duplicate-local") badge = i18nText('sync.local_duplicate_html');
      else if (c.status === "error") badge = i18nText('sync.error_html');
      else if (c.status === "already-synced") badge = i18nText('sync.synced_html');
      var thumb = c.thumbnail_url
        ? '<button type="button" class="sync-thumb-button" title="' + i18nText('sync.zoom_title') + '" aria-label="' + i18nText('sync.zoom_aria_prefix') + esc(c.name || c.path || i18nText('sync.image')) + '" onclick="event.preventDefault();event.stopPropagation();openSyncImagePreview(\'' + escAttrJs(c.thumbnail_url) + '\',\'' + escAttrJs(c.name || c.path || i18nText('sync.remote_image')) + '\')"><img class="sync-thumb" loading="lazy" src="' + esc(c.thumbnail_url) + '" onerror="this.parentNode.classList.add(\'sync-thumb-error\')"></button>'
        : i18nText('sync.no_image_html');
      return (
        '<label class="sync-card ' + (selectable ? "" : "sync-card-disabled") + '">' +
        '<input type="checkbox" class="sync-check" data-i="' + i + '" ' +
        (selectable ? "" : "disabled") + " onchange=\"updateCounts()\">" +
        thumb +
        '<div class="sync-card-meta">' +
        "<div>" + esc(c.name || c.path || i18nText('sync.image')) + "</div>" +
        "<div class='sync-card-sub'>" + esc((c.created_at || "").slice(0, 10)) +
        " · " + fmtBytes(c.size) +
        (c.width ? " · " + c.width + "×" + c.height : "") + "</div>" +
        badge +
        (c.status === "error" ? "<div class='sync-card-sub err'>" + esc(c.reason || "") + "</div>" : "") +
        "</div></label>"
      );
    }).join("");
    updateCounts();
  }

  function fmtBytes(b) {
    if (!b) return "0B";
    if (b < 1024) return b + "B";
    if (b < 1024 * 1024) return (b / 1024).toFixed(0) + "KB";
    return (b / 1024 / 1024).toFixed(1) + "MB";
  }

  window.openSyncImagePreview = function (src, label) {
    if (typeof openLightbox === "function") openLightbox(src, label, "");
  };

  window.updateCounts = function () {
    var checks = document.querySelectorAll("#syncPreview .sync-check");
    var n = 0;
    checks.forEach(function (c) { if (c.checked && !c.disabled) n++; });
    $("syncSelectedCount").textContent = i18nText('sync.selected_prefix') + n;
    $("syncImportNum").textContent = n;
    $("syncImportBtn").disabled = n === 0;
  };

  window.syncSelectAll = function (on) {
    document.querySelectorAll("#syncPreview .sync-check").forEach(function (c) {
      if (!c.disabled) c.checked = on;
    });
    updateCounts();
  };

  window.startSyncImport = function () {
    var id = state.deploymentId;
    if (!id) return;
    var items = [];
    document.querySelectorAll("#syncPreview .sync-check").forEach(function (c) {
      if (c.checked && !c.disabled) {
        var cand = state.filtered[parseInt(c.dataset.i, 10)];
        if (cand) {
          items.push({
            path: cand.path,
            url: cand.url,
            thumbnail_url: cand.thumbnail_url,
            created_at: cand.created_at,
            size: cand.size,
            width: cand.width,
            height: cand.height,
            prompt: cand.prompt || "",
            model: cand.model || "",
          });
        }
      }
    });
    if (!items.length) return;
    $("syncImportBtn").disabled = true;
    _authFetch("/api/sync/import", {
      method: "POST",
      body: JSON.stringify({ deployment_id: id, items: items }),
    })
      .then(readJson)
      .then(function (d) {
        if (d.task_id) pollSyncStatus(d.task_id, items.length);
      })
      .catch(function (e) { alert(i18nText('sync.start_failed_prefix') + e.message); $("syncImportBtn").disabled = false; });
  };

  function pollSyncStatus(taskId, total) {
    $("syncProgressBox").classList.remove("hidden");
    function tick() {
      _authFetch("/api/sync/status/" + taskId)
        .then(readJson)
        .then(function (t) {
          var pct = total ? Math.round((t.done / total) * 100) : 0;
          $("syncProgressFill").style.width = pct + "%";
          $("syncProgressText").textContent =
            i18nText('sync.processed_prefix') + t.done + "/" + total +
            (t.errors && t.errors.length ? i18nText('sync.error_count_prefix') + t.errors.length + "）" : "");
          if (t.status === "done") {
            $("syncProgressText").textContent = i18nText('sync.complete');
            if (typeof loadGallery === "function") loadGallery();
            setTimeout(closeSyncModal, 1500);
          } else {
            setTimeout(tick, 800);
          }
        })
        .catch(function () { setTimeout(tick, 1500); });
    }
    tick();
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function escAttrJs(s) {
    return String(s == null ? "" : s)
      .replace(/\\/g, "\\\\").replace(/'/g, "\\'")
      .replace(/\r/g, "").replace(/\n/g, "\\n");
  }
})();
