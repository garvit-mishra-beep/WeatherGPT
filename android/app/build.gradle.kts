plugins {
  alias(libs.plugins.android.application)
  alias(libs.plugins.compose.compiler)
  alias(libs.plugins.kotlin.serialization)
}

// Google Services plugin is applied when google-services.json is present in the app module root
if (file("google-services.json").exists()) {
    apply(plugin = "com.google.gms.google-services")
}

android {
    namespace = "com.weathergpt"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.weathergpt"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        create("release") {
            val keystorePath = System.getenv("WEATHERGPT_KEYSTORE_FILE")
            val keystorePass = System.getenv("WEATHERGPT_KEYSTORE_PASSWORD")
            val keyAliasVal = System.getenv("WEATHERGPT_KEY_ALIAS")
            val keyPassVal = System.getenv("WEATHERGPT_KEY_PASSWORD")

            if (!keystorePath.isNullOrBlank() && file(keystorePath).exists()) {
                storeFile = file(keystorePath)
                storePassword = keystorePass
                keyAlias = keyAliasVal
                keyPassword = keyPassVal
            }
        }
    }

    val emulatorDebugUrl = "http://10.0.2.2:8000/"
    val physicalDebugUrl = "http://127.0.0.1:8000/"
    val stagingUrl = "https://staging-api.weathergpt.in/"
    val productionUrl = "https://api.weathergpt.in/"

    val debugTarget = (project.findProperty("debugTarget") as String?)
        ?: System.getenv("WEATHERGPT_DEBUG_TARGET")
        ?: "physical"

    val debugDefaultUrl = when (debugTarget.lowercase()) {
        "emulator" -> emulatorDebugUrl
        "staging" -> stagingUrl
        else -> physicalDebugUrl
    }

    val defaultOllamaUrl = "http://192.168.137.1:11434/"
    val defaultOllamaModel = "gemma4:e2b"

    buildTypes {
        debug {
            isMinifyEnabled = false
            buildConfigField("String", "DEFAULT_API_BASE_URL", "\"$debugDefaultUrl\"")
            buildConfigField("String", "DEBUG_PHYSICAL_URL", "\"$physicalDebugUrl\"")
            buildConfigField("String", "DEBUG_EMULATOR_URL", "\"$emulatorDebugUrl\"")
            buildConfigField("String", "STAGING_URL", "\"$stagingUrl\"")
            buildConfigField("String", "PRODUCTION_URL", "\"$productionUrl\"")
            buildConfigField("Boolean", "ENABLE_NETWORK_LOGGING", "true")
            buildConfigField("Boolean", "DEMO_MODE", "true")
            buildConfigField("String", "DEFAULT_OLLAMA_URL", "\"$defaultOllamaUrl\"")
            buildConfigField("String", "DEFAULT_OLLAMA_MODEL", "\"$defaultOllamaModel\"")
        }
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            buildConfigField("String", "DEFAULT_API_BASE_URL", "\"$productionUrl\"")
            buildConfigField("String", "DEBUG_PHYSICAL_URL", "\"$physicalDebugUrl\"")
            buildConfigField("String", "DEBUG_EMULATOR_URL", "\"$emulatorDebugUrl\"")
            buildConfigField("String", "STAGING_URL", "\"$stagingUrl\"")
            buildConfigField("String", "PRODUCTION_URL", "\"$productionUrl\"")
            buildConfigField("Boolean", "ENABLE_NETWORK_LOGGING", "false")
            buildConfigField("Boolean", "DEMO_MODE", "true")
            buildConfigField("String", "DEFAULT_OLLAMA_URL", "\"$defaultOllamaUrl\"")
            buildConfigField("String", "DEFAULT_OLLAMA_MODEL", "\"$defaultOllamaModel\"")

            val releaseSigning = signingConfigs.getByName("release")
            if (releaseSigning.storeFile != null && releaseSigning.storeFile!!.exists()) {
                signingConfig = releaseSigning
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
        aidl = false
        shaders = false
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    testOptions {
        unitTests {
            isReturnDefaultValues = true
        }
    }
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    val composeBom = platform(libs.androidx.compose.bom)
    implementation(composeBom)
    androidTestImplementation(composeBom)

    // Core Android & Kotlin Coroutines
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)

    // Architecture & Lifecycle
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)

    // Compose Foundation (Minimal Shell UI)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.compose.material:material-icons-extended")
    debugImplementation(libs.androidx.compose.ui.tooling)

    // Networking (Retrofit + OkHttp + Serialization)
    implementation(libs.retrofit)
    implementation(libs.retrofit.converter.kotlinx.serialization)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging.interceptor)
    implementation(libs.kotlinx.serialization.json)

    // Firebase Cloud Messaging (BOM-managed)
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)

    // Unit Testing
    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.okhttp.mockwebserver)

    // Instrumented Tests
    androidTestImplementation(libs.androidx.test.core)
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.test.espresso.core)
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
