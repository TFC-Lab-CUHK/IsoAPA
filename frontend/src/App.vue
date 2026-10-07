<template>
  <v-app>
    <!-- Glassmorphism navbar -->
    <v-app-bar
      :elevation="0"
      class="glass-navbar"
      height="60"
    >
      <v-container class="d-flex align-center py-0" style="max-width:1280px;">
        <router-link to="/" class="text-decoration-none d-flex align-center">
          <div class="nav-logo-wrap mr-2">
            <IsoAPAIcon :size="20" style="color:#0D7377;" />
          </div>
          <span class="nav-brand">IsoAPA</span>
        </router-link>

        <v-spacer></v-spacer>

        <nav class="nav-links d-none d-md-flex align-center">
          <router-link to="/" class="nav-link" active-class="nav-link--active">Home</router-link>
          <router-link to="/search" class="nav-link" active-class="nav-link--active">Browse</router-link>
          <router-link to="/compare" class="nav-link" active-class="nav-link--active">Compare</router-link>
          <router-link to="/statistics" class="nav-link" active-class="nav-link--active">Statistics</router-link>
          <router-link to="/download" class="nav-link" active-class="nav-link--active">Download</router-link>
          <router-link to="/help" class="nav-link" active-class="nav-link--active">Help</router-link>
        </nav>

        <v-btn
          class="mobile-nav-toggle d-flex d-md-none"
          icon
          variant="text"
          aria-label="Open navigation menu"
          @click="mobileNavOpen = true"
        >
          <v-icon icon="mdi-menu"></v-icon>
        </v-btn>

      </v-container>
    </v-app-bar>

    <v-navigation-drawer
      v-model="mobileNavOpen"
      class="mobile-nav-drawer"
      location="right"
      temporary
      width="292"
    >
      <div class="mobile-nav-header">
        <div class="d-flex align-center">
          <div class="nav-logo-wrap mr-2">
            <IsoAPAIcon :size="20" style="color:#0D7377;" />
          </div>
          <span class="nav-brand">IsoAPA</span>
        </div>
        <v-btn icon variant="text" size="small" aria-label="Close navigation menu" @click="mobileNavOpen = false">
          <v-icon icon="mdi-close"></v-icon>
        </v-btn>
      </div>
      <nav class="mobile-nav-links">
        <router-link
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="mobile-nav-link"
          active-class="mobile-nav-link--active"
          @click="mobileNavOpen = false"
        >
          <v-icon :icon="link.icon" size="18"></v-icon>
          <span>{{ link.label }}</span>
        </router-link>
      </nav>
    </v-navigation-drawer>

    <v-main>
      <router-view></router-view>
    </v-main>

    <!-- Footer -->
    <footer class="app-footer">
      <v-container style="max-width:1280px;">
        <div class="footer-grid">
          <div class="footer-col">
            <div class="footer-brand d-flex align-center mb-3">
              <IsoAPAIcon :size="18" style="color:#0D7377;" class="mr-2" />
              <span class="footer-brand-name">IsoAPA</span>
              <span class="footer-version">v1.0.0</span>
            </div>
            <p class="footer-desc footer-desc--single-line">Isoform-level alternative polyadenylation database.</p>
            <div class="footer-affiliations" aria-label="Institutional affiliations">
              <a
                class="footer-affiliation-link footer-affiliation-link--cuhk"
                href="https://www.cuhk.edu.hk/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="The Chinese University of Hong Kong"
              >
                <img
                  src="/images/cuhk-logo.png"
                  alt="The Chinese University of Hong Kong"
                  class="footer-affiliation-logo footer-affiliation-logo--cuhk"
                />
              </a>
              <span class="footer-affiliation-divider" aria-hidden="true"></span>
              <a
                class="footer-affiliation-link footer-affiliation-link--sls"
                href="https://www.sls.cuhk.edu.hk/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="School of Life Sciences, The Chinese University of Hong Kong"
              >
                <img
                  src="/images/sls-logo.png"
                  alt="School of Life Sciences, The Chinese University of Hong Kong"
                  class="footer-affiliation-logo footer-affiliation-logo--sls"
                />
              </a>
            </div>
          </div>
          <div class="footer-col">
            <h4 class="footer-heading">Quick Links</h4>
            <div class="footer-links">
              <router-link to="/" class="footer-link">Home</router-link>
              <router-link to="/search" class="footer-link">Browse Data</router-link>
              <router-link to="/compare" class="footer-link">Cross-species Comparison</router-link>
              <router-link to="/statistics" class="footer-link">Statistics</router-link>
              <router-link to="/download" class="footer-link">Download</router-link>
              <router-link to="/api-reference" class="footer-link">API Reference</router-link>
              <router-link to="/help" class="footer-link">Help &amp; Docs</router-link>
            </div>
          </div>
          <div class="footer-col">
            <h4 class="footer-heading">Contact</h4>
            <p class="footer-desc">For questions or feedback, please contact:</p>
            <a href="mailto:tf.chan@cuhk.edu.hk" class="footer-email">tf.chan@cuhk.edu.hk</a>
          </div>
        </div>
        <div class="footer-divider"></div>
        <p class="footer-copy">&copy; 2026 IsoAPA · Ting-Fung Chan Lab, School of Life Sciences, CUHK.</p>
      </v-container>
    </footer>
  </v-app>
</template>

<script setup>
import { ref } from 'vue'
import IsoAPAIcon from '@/components/IsoAPAIcon.vue'

const mobileNavOpen = ref(false)
const navLinks = [
  { to: '/', label: 'Home', icon: 'mdi-home-outline' },
  { to: '/search', label: 'Browse', icon: 'mdi-database-search-outline' },
  { to: '/compare', label: 'Compare', icon: 'mdi-vector-link' },
  { to: '/statistics', label: 'Statistics', icon: 'mdi-chart-box-outline' },
  { to: '/download', label: 'Download', icon: 'mdi-download-outline' },
  { to: '/help', label: 'Help', icon: 'mdi-help-circle-outline' }
]
</script>

<style>
html, body, #app {
  font-family: var(--aa-font-sans) !important;
  overflow-y: auto !important;
}
* {
  font-family: inherit;
}
:root {
  --v-font-family: var(--aa-font-sans);
}
a {
  color: inherit;
}

/* ── Glassmorphism navbar ─────────────────────────────────── */
.glass-navbar {
  background: rgba(248, 252, 252, 0.78) !important;
  backdrop-filter: blur(22px) saturate(180%) !important;
  -webkit-backdrop-filter: blur(22px) saturate(180%) !important;
  border-bottom: 1px solid rgba(13, 115, 119, 0.12) !important;
  box-shadow: 0 10px 32px rgba(15, 23, 42, 0.05) !important;
}

.nav-logo-wrap {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(13, 115, 119, 0.12), rgba(20, 145, 155, 0.18));
  border: 1px solid rgba(13, 115, 119, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-brand {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--aa-teal-800);
}

.nav-links {
  gap: 4px;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  padding: 7px 15px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 700;
  color: var(--aa-slate-600);
  text-decoration: none;
  transition: background 150ms, color 150ms;
  letter-spacing: 0.03em;
}

.nav-link:hover {
  background: rgba(13, 115, 119, 0.08);
  color: #0D7377;
}

.nav-link--active {
  background: rgba(13, 115, 119, 0.11);
  color: var(--aa-teal-800) !important;
  font-weight: 700;
}

.mobile-nav-toggle {
  color: var(--aa-teal-800) !important;
}

.mobile-nav-drawer {
  background: #fbfefd !important;
  border-left: 1px solid rgba(13, 115, 119, 0.12) !important;
}

.mobile-nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 18px 14px;
  border-bottom: 1px solid rgba(13, 115, 119, 0.10);
}

.mobile-nav-links {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
}

.mobile-nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 13px;
  border-radius: 12px;
  color: var(--aa-slate-600);
  font-size: 15px;
  font-weight: 700;
  text-decoration: none;
}

.mobile-nav-link--active {
  background: rgba(13, 115, 119, 0.10);
  color: var(--aa-teal-800) !important;
}

/* ── Footer ───────────────────────────────────────────────── */
.app-footer {
  background:
    linear-gradient(180deg, rgba(248,250,252,0.86), rgba(241,245,249,0.96)),
    radial-gradient(circle at 8% 20%, rgba(13,115,119,0.08), transparent 24%);
  border-top: 1px solid rgba(13, 115, 119, 0.12);
  padding: 48px 0 28px;
}

.footer-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 40px;
  margin-bottom: 32px;
}

@media (max-width: 768px) {
  .app-footer {
    padding: 38px 0 24px;
  }

  .footer-grid {
    grid-template-columns: 1fr;
    gap: 28px;
  }

  .footer-desc--single-line {
    white-space: normal;
  }
}

.footer-brand-name {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.2px;
  color: var(--aa-slate-800);
}

.footer-brand .footer-version {
  margin-left: 10px;
}

.footer-heading {
  font-size: 13.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--aa-slate-500);
  margin-bottom: 14px;
}

.footer-desc {
  font-size: 14.5px;
  color: var(--aa-slate-600);
  line-height: 1.6;
  margin: 0 0 8px;
}

.footer-desc--single-line {
  white-space: nowrap;
}

.footer-version {
  font-size: 12.5px;
  color: var(--aa-slate-500);
  line-height: 1;
}

.footer-affiliations {
  display: flex;
  align-items: center;
  gap: 18px;
  width: min(500px, 100%);
  margin-top: 22px;
}

.footer-affiliation-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0.9;
  transition: opacity 150ms ease, transform 150ms ease;
}

.footer-affiliation-link:hover {
  opacity: 1;
  transform: translateY(-1px);
}

.footer-affiliation-logo {
  display: block;
  width: auto;
  object-fit: contain;
}

.footer-affiliation-logo--cuhk {
  height: 66px;
}

.footer-affiliation-logo--sls {
  height: 52px;
}

.footer-affiliation-divider {
  width: 1px;
  height: 52px;
  background: rgba(100, 116, 139, 0.34);
  flex: 0 0 auto;
}

.footer-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.footer-link {
  font-size: 14.5px;
  color: var(--aa-slate-600);
  text-decoration: none;
  transition: color 150ms;
}

.footer-link:hover {
  color: var(--aa-teal-700);
}

.footer-email {
  font-size: 14.5px;
  color: var(--aa-teal-700);
  text-decoration: none;
  font-weight: 500;
}

.footer-email:hover {
  text-decoration: underline;
}

.footer-divider {
  height: 1px;
  background: rgba(13, 115, 119, 0.12);
  margin-bottom: 20px;
}

.footer-copy {
  font-size: 13.5px;
  color: var(--aa-slate-500);
  text-align: center;
  margin: 0;
}

</style>
