import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: window
    flags: Qt.Dialog | Qt.FramelessWindowHint
    visible: true
    width: 280
    height: 300
    font.family: "SF Pro Display"
    color: "transparent"
    
    onClosing: {
        hpa.setResult("fail");
    }

    Rectangle {
        opacity: 0.9
        anchors.fill: parent
        color: "#161616"
        radius: 12
        layer.enabled: true
    }

    Item {
        id: mainLayout
        anchors.fill: parent
        anchors.margins: 12
        
        Keys.onEscapePressed: (e) => {
            hpa.setResult("fail");
        }
        Keys.onReturnPressed: (e) => {
            if (passwordField.text.length > 0) {
                hpa.setResult("auth:" + passwordField.text);
            }
        }
        Keys.onEnterPressed: (e) => {
            if (passwordField.text.length > 0) {
                hpa.setResult("auth:" + passwordField.text);
            }
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            Label {
                text: ""
                font.family: "FontAwesome"
                color: "white"
                font.pixelSize: 56
                font.bold: false
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                color: "#dddddd"
                font.pixelSize: 16
                font.weight: Font.DemiBold
                text: "Autenticação necessária"
                Layout.alignment: Qt.AlignHCenter
                Layout.maximumWidth: parent.width
                elide: Text.ElideRight
                wrapMode: Text.WordWrap
            }

            Label {
                color: "#d0d0d0"
                font.pixelSize: 14
                text: "A aplicação precisa de acesso sudo para executar esta operação."
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
            }

            TextField {
                id: passwordField
                placeholderText: "Password"
                echoMode: TextInput.Password
                focus: true
                color: "white"
                placeholderTextColor: "#888888"
                font.pixelSize: 12
                Layout.fillWidth: true
                leftPadding: 14
                rightPadding: 14
                topPadding: 10
                bottomPadding: 10

                background: Rectangle {
                    radius: 10
                    color: "#2a2a2a"
                    border.color: passwordField.activeFocus ? "#4A90E2" : "#3a3a3a"
                    border.width: passwordField.activeFocus ? 2 : 1
                }

                Connections {
                    target: hpa
                    function onFocusField() {
                        passwordField.focus = true;
                    }
                    function onBlockInput(block) {
                        passwordField.readOnly = block;
                        if (!block) {
                            passwordField.focus = true;
                            passwordField.selectAll();
                        }
                    }
                }
            }

           

            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 10

                Button {
                    text: "Cancel"
                    font.pixelSize: 16
                    font.bold: true
                    Layout.fillWidth: true
                    Layout.preferredWidth: parent.width * 0.5
                    padding: 10

                    onClicked: hpa.setResult("fail")

                    background: Rectangle {
                        radius: 8
                        color: "#3a3a3a"
                        border.color: "#27292b"
                        border.width: 1
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onEntered: parent.color = "#3f3f3f"
                            onExited: parent.color = "#3a3a3a"
                        }
                    }

                    contentItem: Text {
                        text: parent.text
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Button {
                    text: "Authenticate"
                    font.pixelSize: 16
                    font.bold: true
                    Layout.fillWidth: true
                    Layout.preferredWidth: parent.width * 0.5
                    padding: 10

                    onClicked: {
                        if (passwordField.text.length > 0) {
                            hpa.setResult("auth:" + passwordField.text);
                        }
                    }

                    background: Rectangle {
                        radius: 8
                        border.color: "#ffffff"
                        border.width: 0.4
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#3468da" }
                            GradientStop { position: 1.0; color: "#2e5cca" }
                        }               
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onEntered: parent.color = "#3d7aff"
                            onExited: parent.color = "#3468da"
                        }
                    }

                    contentItem: Text {
                        text: parent.text
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
}