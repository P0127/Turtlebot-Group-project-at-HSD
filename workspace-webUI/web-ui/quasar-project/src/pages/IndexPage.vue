<template>
  <q-page class="landing-page">

    <div class="content">

      <!-- LEFT: Robot -->
      <div class="robot-container">
        <img
          src="src/assets/roboter1.png"
          alt="TurtleBot"
          class="robot-image"
        />
      </div>

      <!-- RIGHT: Text + Button -->
      <div class="text-container">
        <h1 class="title">TurtleBot</h1>
        <h2 class="subtitle">Communicator</h2>

        <q-btn
          label="Start"
          class="start-button"
          unelevated
          rounded
          @click="goToControl"
        />
      </div>

    </div>

    <!-- Bottom right logo -->
    <img
      src="src/assets/roboter2.png"
      alt="TurtleBot Logo"
      class="corner-logo"
    />

  </q-page>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goToControl = () => {
  router.push('/control')
}
</script>

<style scoped>
/* -------------------------------
   PAGE BACKGROUND
-------------------------------- */
.landing-page {
  height: 100vh;
  background: linear-gradient(
    135deg,
    #dcdcdc 0%,
    #f0f0f0 45%,
    #ffffff 100%
  );
  position: relative;
  overflow: hidden;
}

/* -------------------------------
   MAIN LAYOUT
-------------------------------- */
.content {
  height: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 5rem;

  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* -------------------------------
   ROBOT
-------------------------------- */
.robot-container {
  flex: 1;
  display: flex;
  justify-content: center;
}

.robot-image {
  height: 420px;
  object-fit: contain;
}

/* -------------------------------
   TEXT
-------------------------------- */
.text-container {
  flex: 1;
  text-align: left;
}

.title {
  font-size: 3.8rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  margin: 0;
  color: #2b2b2b;
}

.subtitle {
  font-size: 3.2rem;
  font-weight: 400;
  margin: 0 0 3rem 0;
  color: #4a4a4a;
}

/* -------------------------------
   BUTTON
-------------------------------- */
.start-button {
  padding: 0.9rem 3.2rem;
  font-size: 1.2rem;
  text-transform: none;
  border: 2px solid #2b2b2b;
  color: #2b2b2b;
  background: transparent;
  transition: all 0.25s ease;
}

.start-button:hover {
  background: #2b2b2b;
  color: #ffffff;
}

/* -------------------------------
   LOGO
-------------------------------- */
.corner-logo {
  position: absolute;
  bottom: 2rem;
  right: 2.5rem;
  height: 70px;
  opacity: 0.9;
}
</style>