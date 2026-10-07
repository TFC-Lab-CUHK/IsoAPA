import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import Search from '@/views/Search.vue'
import LocusDetail from '@/views/LocusDetail.vue'
import GeneDetail from '@/views/GeneDetail.vue'
import Statistics from '@/views/Statistics.vue'
import Download from '@/views/Download.vue'
import Help from '@/views/Help.vue'
import ApiReference from '@/views/ApiReference.vue'
import CrossSpecies from '@/views/CrossSpecies.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/search',
    name: 'Search',
    component: Search
  },
  {
    path: '/compare',
    name: 'CrossSpecies',
    component: CrossSpecies
  },
  {
    path: '/locus/:transcriptId',
    name: 'LocusDetail',
    component: LocusDetail
  },
  {
    path: '/gene/:geneId',
    name: 'GeneDetail',
    component: GeneDetail
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: Statistics
  },
  {
    path: '/download',
    name: 'Download',
    component: Download
  },
  {
    path: '/help',
    name: 'Help',
    component: Help
  },
  {
    path: '/api-reference',
    name: 'ApiReference',
    component: ApiReference
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) {
      return new Promise((resolve) => {
        requestAnimationFrame(() => {
          resolve({
            el: to.hash,
            top: 72,
            behavior: 'smooth'
          })
        })
      })
    }
    // Staying on the same route means the view only wrote its state into the
    // query — CrossSpecies does this on every selection, sample, view and scale
    // change. That is not a page change, so leave the reader where they are
    // instead of throwing them back to the top of the page.
    if (to.path === from.path) return false
    return { top: 0, left: 0 }
  }
})

export default router
