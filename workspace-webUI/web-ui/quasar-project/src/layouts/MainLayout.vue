<template>
  <q-layout view="lHh Lpr lFf">
    <!-- Header -->
    <q-header elevated class="header">
      <q-toolbar class="toolbar">
        <!-- Titel links -->
        <q-toolbar-title class="title">
          Tales from the Turtlebot - Take Control
        </q-toolbar-title>

        <!-- Logo rechts -->
        <img :src="logo" alt="Logo" class="logo" />
      </q-toolbar>
    </q-header>

    <!-- Page Container -->
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import logo from 'src/assets/roboter2.png';
</script>

<style scoped>
/* Hochwertiger, minimalistischer Header */
.header {
  background-color: #f8f8f8; /* helles Grau */
  color: #1c1c1e; /* dunkles Grau */
  font-family: -apple-system, BlinkMacSystemFont, "San Francisco", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  border-bottom: 1px solid rgba(60,60,67,0.1); /* feiner Schatten */
  backdrop-filter: blur(12px);
}

/* Toolbar Styling */
.toolbar {
  display: flex;
  justify-content: space-between; /* Titel links, Logo rechts */
  align-items: center;
  padding: 0 24px;
  min-height: 64px;
}

/* Titel Styling */
.title {
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 0.25px;
  color: #1c1c1e;
}

/* Logo Styling */
.logo {
  height: 36px;
  object-fit: contain;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Subtile Hover-Animation */
.logo:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(0,0,0,0.08);
}
</style>