"use client";

import { useState } from "react";
import { Settings, User, Lock, Bell, Globe } from "lucide-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <Settings className="h-6 w-6" />
        <h1 className="text-2xl font-bold">Configuración</h1>
      </div>
      
      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar de navegación */}
        <div className="w-full md:w-64 flex-shrink-0">
          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab("profile")}
              className={`flex items-center w-full px-4 py-2 text-sm font-medium rounded-md ${
                activeTab === "profile"
                  ? "bg-primary/10 text-primary"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <User className="h-4 w-4 mr-3" />
              Perfil
            </button>
            
            <button
              onClick={() => setActiveTab("security")}
              className={`flex items-center w-full px-4 py-2 text-sm font-medium rounded-md ${
                activeTab === "security"
                  ? "bg-primary/10 text-primary"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <Lock className="h-4 w-4 mr-3" />
              Seguridad
            </button>
            
            <button
              onClick={() => setActiveTab("notifications")}
              className={`flex items-center w-full px-4 py-2 text-sm font-medium rounded-md ${
                activeTab === "notifications"
                  ? "bg-primary/10 text-primary"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <Bell className="h-4 w-4 mr-3" />
              Notificaciones
            </button>
            
            <button
              onClick={() => setActiveTab("language")}
              className={`flex items-center w-full px-4 py-2 text-sm font-medium rounded-md ${
                activeTab === "language"
                  ? "bg-primary/10 text-primary"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <Globe className="h-4 w-4 mr-3" />
              Idioma y Región
            </button>
          </nav>
        </div>
        
        {/* Contenido */}
        <div className="flex-1 bg-white p-6 rounded-lg shadow">
          {activeTab === "profile" && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Perfil de Usuario</h2>
              <p className="text-gray-600">Configura tu información personal.</p>
              {/* Aquí irá el formulario de perfil */}
            </div>
          )}
          
          {activeTab === "security" && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Seguridad</h2>
              <p className="text-gray-600">Gestiona tu contraseña y seguridad de la cuenta.</p>
              {/* Aquí irán las opciones de seguridad */}
            </div>
          )}
          
          {activeTab === "notifications" && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Preferencias de Notificación</h2>
              <p className="text-gray-600">Configura cómo y cuándo recibir notificaciones.</p>
              {/* Aquí irán las opciones de notificaciones */}
            </div>
          )}
          
          {activeTab === "language" && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Idioma y Región</h2>
              <p className="text-gray-600">Selecciona tu idioma y configuración regional preferidos.</p>
              {/* Aquí irán las opciones de idioma */}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
