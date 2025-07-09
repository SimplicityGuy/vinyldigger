import { spawn } from 'child_process'

async function globalTeardown() {
  // Only stop services if we started them
  if (!process.env.CI && !process.env.SKIP_DOCKER_SETUP && !process.env.KEEP_SERVICES_RUNNING) {
    console.log('Stopping test services...')

    const stopProcess = spawn('docker-compose', [
      '-f', 'docker-compose.test.yml',
      'down', '-v'
    ], {
      cwd: '..',
      shell: true
    })

    await new Promise<void>((resolve) => {
      stopProcess.on('close', () => {
        console.log('Test services stopped')
        resolve()
      })
    })
  }
}

export default globalTeardown
