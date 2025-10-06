"use client"

import { useState } from "react"
import { Send, MessageCircle, Bot, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"

interface HelpChatProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  context?: {
    hsCode: string
    confidence: number
    inputText?: string
  }
}

interface Message {
  id: string
  type: "user" | "bot"
  content: string
  timestamp: Date
}

export function HelpChat({ open, onOpenChange, context }: HelpChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "bot",
      content: `Hola! Soy tu asistente de clasificación HS. Veo que tienes una clasificación para el código ${context?.hsCode || "N/A"} con ${Math.round((context?.confidence || 0) * 100)}% de confianza. ¿En qué puedo ayudarte?`,
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false)

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: inputValue,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")
    setIsTyping(true)

    // Simulate bot response
    setTimeout(() => {
      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        type: "bot",
        content: getBotResponse(inputValue, context),
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, botResponse])
      setIsTyping(false)
    }, 1500)
  }

  const getBotResponse = (userInput: string, context?: any): string => {
    const input = userInput.toLowerCase()

    if (input.includes("confianza") || input.includes("confidence")) {
      return `La confianza del ${Math.round((context?.confidence || 0) * 100)}% indica ${
        (context?.confidence || 0) >= 0.85
          ? "alta precisión"
          : (context?.confidence || 0) >= 0.6
            ? "precisión media - considera revisar alternativas"
            : "baja precisión - recomiendo revisión manual"
      }. ¿Te gustaría que explique los factores que influyeron en esta clasificación?`
    }

    if (input.includes("alternativa") || input.includes("alternative")) {
      return "Puedes hacer clic en cualquiera de las alternativas mostradas para ver una explicación comparativa. Las alternativas están ordenadas por confianza descendente."
    }

    if (input.includes("exportar") || input.includes("export")) {
      return "Puedes exportar los resultados en formato PDF (incluye explicación completa) o CSV (datos tabulares). El PDF es ideal para reportes, mientras que CSV es mejor para análisis de datos."
    }

    if (input.includes("auditoría") || input.includes("audit")) {
      return "Si la confianza es baja (<60%), puedes marcar el caso para auditoría. Esto enviará el caso a un auditor humano para revisión y corrección si es necesario."
    }

    return "Entiendo tu consulta. Puedo ayudarte con: explicaciones de confianza, alternativas de clasificación, proceso de exportación, o marcado para auditoría. ¿Sobre qué te gustaría saber más?"
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-96 p-0">
        <div className="flex flex-col h-full">
          <SheetHeader className="p-6 border-b">
            <SheetTitle className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              Asistente de Clasificación
            </SheetTitle>
          </SheetHeader>

          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${message.type === "user" ? "justify-end" : "justify-start"}`}
                >
                  {message.type === "bot" && (
                    <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                      <Bot className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}

                  <div
                    className={`max-w-[80%] p-3 rounded-2xl ${
                      message.type === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{message.content}</p>
                    <p className="text-xs opacity-70 mt-1">{message.timestamp.toLocaleTimeString()}</p>
                  </div>

                  {message.type === "user" && (
                    <div className="w-8 h-8 bg-muted rounded-full flex items-center justify-center">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}

              {isTyping && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary-foreground" />
                  </div>
                  <div className="bg-muted p-3 rounded-2xl">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" />
                      <div
                        className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
                        style={{ animationDelay: "0.1s" }}
                      />
                      <div
                        className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
                        style={{ animationDelay: "0.2s" }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>

          <div className="p-4 border-t">
            <div className="flex gap-2">
              <Input
                placeholder="Escribe tu pregunta..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
                disabled={isTyping}
              />
              <Button size="icon" onClick={handleSendMessage} disabled={!inputValue.trim() || isTyping}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
