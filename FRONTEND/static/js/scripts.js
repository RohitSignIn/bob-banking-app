/**
 * scripts.js  —  SecureBank optional client-side helpers
 * No business logic lives here. Validation is enforced server-side.
 */

/**
 * Auto-dismiss Bootstrap alert components after 5 seconds.
 * Works for any .alert element that was rendered by the flash system.
 */
document.addEventListener("DOMContentLoaded", function () {
  const alerts = document.querySelectorAll(".alert.alert-success, .alert.alert-info");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 5000);
  });
});
