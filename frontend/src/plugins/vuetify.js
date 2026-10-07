import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const isoapaTheme = {
  dark: false,
  colors: {
    background: '#F5F8FA',
    surface: '#FFFFFF',
    'surface-variant': '#E7EEF1',
    primary: '#0D7377',
    'primary-darken-1': '#0A5C5F',
    secondary: '#14919B',
    accent: '#355C7D',
    error: '#D64545',
    info: '#3D7EBF',
    success: '#3D9970',
    warning: '#C9821A',
  }
}

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'isoapaTheme',
    themes: {
      isoapaTheme,
    }
  },
  defaults: {
    VBtn: {
      rounded: 'lg',
      style: 'letter-spacing: 0.01em; font-weight: 600;',
    },
    VCard: {
      rounded: 'xl',
      elevation: 0,
      class: 'aa-card',
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable',
      rounded: 'lg',
    },
    VSelect: {
      variant: 'outlined',
      density: 'comfortable',
      rounded: 'lg',
    },
    VAutocomplete: {
      variant: 'outlined',
      density: 'comfortable',
      rounded: 'lg',
    },
    VDataTable: {
      density: 'comfortable',
    },
    VTable: {
      density: 'comfortable',
    }
  }
})
