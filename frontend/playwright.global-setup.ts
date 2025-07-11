import { spawn } from 'child_process'

async function globalSetup() {
  // Only start services if not in CI and not already running
  if (!process.env.CI && !process.env.SKIP_DOCKER_SETUP) {
    console.log('Starting test services...')

    // Check if services are already running
    const checkProcess = spawn('docker-compose', [
      '-f', 'docker-compose.test.yml',
      'ps', '-q'
    ], {
      cwd: '..',
      shell: true
    })

    const isRunning = await new Promise<boolean>((resolve) => {
      let output = ''
      checkProcess.stdout.on('data', (data) => {
        output += data.toString()
      })
      checkProcess.on('close', () => {
        resolve(output.trim().length > 0)
      })
    })

    if (!isRunning) {
      // Start docker-compose services
      spawn('docker-compose', [
        '-f', 'docker-compose.test.yml',
        'up', '-d'
      ], {
        cwd: '..',
        shell: true,
        detached: false
      })

      // Wait for services to be ready
      console.log('Waiting for services to be healthy...')
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Services failed to start within timeout'))
        }, 60000)

        const checkHealth = setInterval(async () => {
          const healthCheck = spawn('docker-compose', [
            '-f', 'docker-compose.test.yml',
            'ps'
          ], {
            cwd: '..',
            shell: true
          })

          let output = ''
          healthCheck.stdout.on('data', (data) => {
            output += data.toString()
          })

          healthCheck.on('close', () => {
            // Check if all required services are healthy
            const lines = output.split('\n')
            const backendHealthy = lines.some(line =>
              line.includes('backend') && line.includes('healthy')
            )
            const postgresHealthy = lines.some(line =>
              line.includes('postgres') && line.includes('healthy')
            )
            const redisHealthy = lines.some(line =>
              line.includes('redis') && line.includes('healthy')
            )
            const frontendHealthy = lines.some(line =>
              line.includes('frontend') && line.includes('healthy')
            )

            if (backendHealthy && postgresHealthy && redisHealthy && frontendHealthy) {
              clearInterval(checkHealth)
              clearTimeout(timeout)
              console.log('All services are healthy!')
              resolve()
            }
          })
        }, 2000)
      })

      // Additional wait to ensure services are fully ready
      await new Promise(resolve => setTimeout(resolve, 5000))

      // Verify backend is accessible via health endpoint
      try {
        const healthCheckResponse = await fetch('http://localhost:8000/health')
        if (!healthCheckResponse.ok) {
          throw new Error(`Backend health check failed with status: ${healthCheckResponse.status}`)
        }
      } catch (error) {
        console.error('Backend health check error:', error)
        throw new Error('Backend is not accessible at http://localhost:8000/health')
      }

      // Verify frontend is accessible
      try {
        const frontendCheckResponse = await fetch('http://localhost:3000')
        if (!frontendCheckResponse.ok) {
          console.error(`Frontend check failed with status: ${frontendCheckResponse.status}`)
        }
      } catch (error) {
        console.error('Frontend check error:', error)
        throw new Error('Frontend is not accessible at http://localhost:3000')
      }
    } else {
      console.log('Test services are already running')
    }
  }

  return async () => {
    // Teardown is handled by playwright.global-teardown.ts
  }
}

export default globalSetup
