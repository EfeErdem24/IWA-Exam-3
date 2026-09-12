document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('.alert:not(.alert-danger)');
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 6000);
  });
});
